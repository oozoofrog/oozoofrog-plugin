import AppKit
import SceneKit

private final class SpatialAccessibilityElement: NSAccessibilityElement {
    var press: (() -> Void)?
    override func accessibilityPerformPress() -> Bool {
        guard let press else { return false }
        // Return the AX acknowledgement before a sheet changes the window's modal state.
        DispatchQueue.main.async(execute:press)
        return true
    }
}

/// Native glyph rasterization retains SceneKit depth, transforms and hit regions.
@MainActor private final class SpatialTextNode: SCNNode {
    var value:String
    var color:NSColor
    var font:NSFont
    let textSize:CGSize
    let baseSize:CGFloat
    let weight:NSFont.Weight
    let body:Bool
    init(_ value:String,size:CGSize,fontSize:CGFloat,weight:NSFont.Weight,color:NSColor,body:Bool) {
        self.value = value; textSize = size; baseSize = fontSize; self.weight = weight
        self.color = color; self.body = body; font = .systemFont(ofSize:fontSize,weight:weight)
        super.init()
        let plane = SCNNode(geometry:SCNPlane(width:size.width,height:size.height))
        plane.position = SCNVector3(size.width/2,size.height/2,0); addChildNode(plane); redraw()
    }
    required init?(coder:NSCoder) { fatalError("init(coder:) is unavailable") }
    func redraw() {
        let scale:CGFloat = 3
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:Int(ceil(textSize.width*scale)),pixelsHigh:Int(ceil(textSize.height*scale)),bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0), let context = NSGraphicsContext(bitmapImageRep:bitmap) else { return }
        NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = context
        context.cgContext.scaleBy(x:scale,y:scale)
        context.cgContext.translateBy(x:0,y:textSize.height); context.cgContext.scaleBy(x:1,y:-1)
        context.cgContext.setShouldAntialias(true)
        NSGraphicsContext.current = NSGraphicsContext(cgContext:context.cgContext,flipped:true)
        let (storage,layout,container) = SpatialWorkspace.textLayout(value,font:font,color:color,size:textSize,body:body)
        let range = layout.glyphRange(for:container)
        layout.drawGlyphs(forGlyphRange:range,at:.zero)
        withExtendedLifetime(storage) {}
        NSGraphicsContext.restoreGraphicsState()
        let m = SCNMaterial(); m.lightingModel = .constant; m.isDoubleSided = true; m.diffuse.contents = bitmap.cgImage
        m.diffuse.minificationFilter = .linear; m.diffuse.magnificationFilter = .linear; m.diffuse.mipFilter = .none; m.diffuse.maxAnisotropy = 8
        childNodes.first?.geometry?.materials = [m]
    }
}

/// AppKit owns the editor; everything above it shares this native 3D scene and one motion clock.
@MainActor final class SpatialWorkspace: SCNView {
    var onCommand: (String) -> Void = { _ in }
    private let world = SCNNode(), cameraNode = SCNNode(), core = SCNNode(), orbits = SCNNode()
    private var modules: [String:SCNNode] = [:]
    private var borders: [String:SCNNode] = [:]
    private var surfaces: [(SCNNode,String)] = []
    private var routes: [String:SCNNode] = [:]
    private var selected = ""
    private var linked = false
    private var orbitTime = 0.0
    private var textNodes: [String:SpatialTextNode] = [:]
    private var readingFont = NSFont.systemFont(ofSize:19,weight:.medium)
    private var targets: [(String,SCNNode,CGSize,SpatialAccessibilityElement)] = []
    private var state = RunPresentationState()
    private var queued: [RunPresentationState] = []
    private var motion = SpatialMotion()
    private var timer: Timer?
    private var lastTick = ProcessInfo.processInfo.systemUptime
    private var active = false, pendingPause = false, paused = false
    private var sourcePage = 0, resultPage = 0, historyPage = 0
    private var yaw: Double = -0.07, pitch: Double = 0.025
    private var yawTarget: Double = -0.07, pitchTarget: Double = 0.025
    private var resultRevealAt: Double?
    private var dragPoint: NSPoint?
    private var transfers: [(SCNNode, Double, Bool)] = []
    private var sceneDirty = true
    private var sourcePages = [String](), resultPages = [String]()
    private var outline = NSColor(calibratedRed:0.10,green:0.23,blue:0.25,alpha:1)
    private var accent = NSColor.systemTeal
    private var ink = NSColor.labelColor
    private var secondary = NSColor.secondaryLabelColor

    override init(frame: NSRect, options: [String:Any]? = nil) {
        super.init(frame:frame,options:options)
        scene = SCNScene(); scene!.rootNode.addChildNode(world)
        cameraNode.camera = SCNCamera(); cameraNode.camera!.fieldOfView = 42
        cameraNode.camera!.zNear = 1; cameraNode.camera!.zFar = 5000
        scene!.rootNode.addChildNode(cameraNode); pointOfView = cameraNode
        antialiasingMode = .multisampling4X; allowsCameraControl = false
        setAccessibilityElement(false)
        makeWorld(); updateAppearance(); renderState()
        timer = Timer.scheduledTimer(withTimeInterval:1.0/60,repeats:true) { [weak self] _ in MainActor.assumeIsolated { self?.tick() } }
    }
    required init?(coder:NSCoder) { fatalError("init(coder:) is unavailable") }
    deinit { timer?.invalidate() }
    override var acceptsFirstResponder: Bool { true }

    private func material(_ color:NSColor) -> SCNMaterial {
        let m = SCNMaterial(); m.lightingModel = .constant; m.diffuse.contents = color; m.isDoubleSided = true; return m
    }
    /// Three diffuse bands and a hard highlight. The normal stays in view space,
    /// so the same camera and geometry still determine the volume and occlusion.
    private func toonMaterial(_ color:NSColor) -> SCNMaterial {
        let m = material(color)
        m.shaderModifiers = [.surface: """
        #pragma body
        float3 n = normalize(_surface.normal);
        float shade = dot(n, normalize(float3(-0.45, 0.65, 0.85)));
        float band = shade > 0.55 ? 1.0 : (shade > 0.0 ? 0.76 : 0.46);
        _surface.diffuse.rgb *= band;
        float3 halfVector = normalize(normalize(float3(-0.45, 0.65, 0.85)) + normalize(_surface.view));
        if (dot(n, halfVector) > 0.985) {
            _surface.diffuse.rgb = mix(_surface.diffuse.rgb, float3(1.0), 0.65);
        }
        """]
        return m
    }
    private func sphereOutline(radius:CGFloat, at position:SCNVector3, parent:SCNNode) {
        let sphere = SCNSphere(radius:radius); sphere.segmentCount = 64
        let node = SCNNode(geometry:sphere); node.position = position
        parent.addChildNode(node); surfaces.append((node,"outline"))
    }
    private func text(_ key:String, _ value:String, at p:SCNVector3, width:CGFloat, height:CGFloat = 32, size:CGFloat = 15, color:NSColor? = nil, command:String? = nil) {
        let body = key == "source" || key == "result"
        let weight:NSFont.Weight = .medium
        let node = SpatialTextNode(value,size:CGSize(width:width,height:height),fontSize:size,weight:weight,color:color ?? ink,body:body)
        node.position = p; node.name = command; world.addChildNode(node); textNodes[key] = node
        let ax = SpatialAccessibilityElement(); ax.setAccessibilityParent(self)
        ax.setAccessibilityRole(command == nil ? .staticText : .button); ax.setAccessibilityLabel(value)
        ax.setAccessibilityEnabled(true)
        if let command {
            let hit = SCNNode(geometry:SCNPlane(width:width,height:height)); hit.position = SCNVector3(width/2,height/2,-0.5)
            let invisible = material(.clear); invisible.colorBufferWriteMask = []; invisible.writesToDepthBuffer = false
            hit.geometry!.materials = [invisible]; hit.name = command; node.addChildNode(hit)
            ax.press = { [weak self] in self?.command(command) }
        }
        targets.append((key,node,CGSize(width:width,height:height),ax))
    }
    /// Every module owns its text, hit regions and plate in the same coordinate space.
    private func module(_ key:String, rect:CGRect, depth:CGFloat, keys:[String], stack:Bool = false, output:Bool = false) {
        let group = SCNNode(); world.addChildNode(group); modules[key] = group
        func slab(_ r:CGRect,_ z:CGFloat,_ thickness:CGFloat,_ role:String) -> SCNNode {
            let box = SCNBox(width:r.width,height:r.height,length:thickness,chamferRadius:3)
            let node = SCNNode(geometry:box); node.position = SCNVector3(r.midX,r.midY,z)
            group.addChildNode(node); surfaces.append((node,role)); return node
        }
        if stack {
            _ = slab(rect.offsetBy(dx:-10,dy:-12),depth-20,4,"paper")
            _ = slab(rect.offsetBy(dx:-5,dy:-6),depth-10,4,"paper")
        }
        _ = slab(rect.offsetBy(dx:7,dy:-9),depth-9,4,"shadow")
        let border = slab(rect.insetBy(dx:-2.4,dy:-2.4),depth-1,6,"border")
        borders[key] = border
        _ = slab(rect,depth,6,"panel")
        // Cap and footer delimiters remain part of the plate as it lifts.
        for y in [rect.maxY-35,rect.minY+75] where key == "source" || key == "result" {
            _ = slab(CGRect(x:rect.minX+1,y:y,width:rect.width-2,height:1.2),depth+3.5,0.5,"line")
        }
        if output { _ = slab(CGRect(x:rect.minX+4,y:rect.maxY-2,width:rect.width-8,height:2),depth+4,1,"energy") }
        if stack { _ = slab(CGRect(x:rect.minX+2,y:rect.minY+4,width:2,height:rect.height-8),depth+4,1,"line") }
        for key in keys { if let node = textNodes[key] { group.addChildNode(node) } }
    }
    private func makeWorld() {
        text("brand","JEV",at:SCNVector3(-440,270,0),width:100,size:25,color:accent,command:"home")
        text("target","맡길 일을 입력해 주세요",at:SCNVector3(-300,272,-12),width:620,size:13,color:secondary)
        text("sourceRole","SOURCE · 원문 / 읽기 전용",at:SCNVector3(-440,201,-28),width:295,height:28,size:13)
        text("sourceTitle","원문",at:SCNVector3(-440,151,-28),width:295,height:44,size:17,color:accent,command:"source")
        text("source","원문이 필요한 요청이면\n확인한 문서가 여기에 나타납니다.",at:SCNVector3(-440,-48,-28),width:295,height:195,size:15)
        text("sourcePage","",at:SCNVector3(-440,-91,-28),width:190,height:28,size:13,color:secondary)
        text("sourceNext","다음 쪽",at:SCNVector3(-235,-96,-28),width:90,height:32,size:14,color:accent,command:"sourceNext")
        text("sourceFull","원문 전문",at:SCNVector3(-440,-121,-28),width:120,height:28,size:13,color:accent,command:"sourceFull")
        module("source",rect:CGRect(x:-456,y:-139,width:334,height:377),depth:-32,keys:["sourceRole","sourceTitle","source","sourcePage","sourceNext","sourceFull"],stack:true)

        text("requestTitle","COMMAND · 요청",at:SCNVector3(-90,210,-61),width:205,height:28,size:13,color:secondary,command:"request")
        text("request","목표와 작업 범위",at:SCNVector3(-90,132,-61),width:205,height:73,size:14,color:secondary,command:"requestFull")
        module("request",rect:CGRect(x:-106,y:121,width:237,height:117),depth:-65,keys:["requestTitle","request"])

        text("resultRole","OUTPUT · 결과 / 응답 대기",at:SCNVector3(171,201,32),width:295,height:28,size:13)
        text("resultTitle","결과",at:SCNVector3(171,151,32),width:295,height:44,size:17,color:accent,command:"result")
        text("result","실행한 작업의 결과를\n이 공간에서 확인할 수 있습니다.",at:SCNVector3(171,-48,32),width:295,height:195,size:15)
        text("resultPage","",at:SCNVector3(171,-91,32),width:190,height:28,size:13,color:secondary)
        text("resultNext","다음 쪽",at:SCNVector3(376,-96,32),width:90,height:32,size:14,color:accent,command:"resultNext")
        text("resultFull","결과 전문 · 복사",at:SCNVector3(171,-121,32),width:180,height:28,size:13,color:accent,command:"resultFull")
        module("result",rect:CGRect(x:155,y:-139,width:334,height:377),depth:28,keys:["resultRole","resultTitle","result","resultPage","resultNext","resultFull"],output:true)

        let coreGroup = SCNNode(); world.addChildNode(coreGroup); modules["core"] = coreGroup
        coreGroup.addChildNode(core); core.position = SCNVector3(20,35,68); core.addChildNode(orbits)
        let globe = SCNSphere(radius:48); globe.segmentCount = 64
        let shell = SCNNode(geometry:globe); core.addChildNode(shell); surfaces.append((shell,"shell"))
        sphereOutline(radius:50,at:SCNVector3Zero,parent:core)
        let nucleus = SCNNode(geometry:SCNSphere(radius:12)); core.addChildNode(nucleus); surfaces.append((nucleus,"nucleus"))
        nucleus.position.z = 62
        sphereOutline(radius:13.3,at:nucleus.position,parent:core)
        for index in 0..<4 {
            let torus = SCNTorus(ringRadius:CGFloat(51+index*2),pipeRadius:1.1)
            torus.ringSegmentCount = 96; torus.pipeSegmentCount = 8
            let ring = SCNNode(geometry:torus)
            ring.eulerAngles = SCNVector3(Double.pi/2,Double(index)*Double.pi/4,index == 3 ? Double.pi/2 : 0)
            orbits.addChildNode(ring); surfaces.append((ring,"energy"))
        }
        text("coreTitle","JEV · 실행 코어",at:SCNVector3(-43,-43,72),width:155,height:28,size:13,color:accent,command:"core")
        text("coreLabel","요청을 기다리는 중",at:SCNVector3(-65,-67,72),width:190,height:28,size:13,color:secondary)
        text("provenance","",at:SCNVector3(-65,-140,72),width:190,height:64,size:13,color:secondary,command:"trace")
        for key in ["coreTitle","coreLabel","provenance"] { coreGroup.addChildNode(textNodes[key]!) }
        let keyLight = SCNNode(); keyLight.light = SCNLight(); keyLight.light!.type = .omni; keyLight.light!.intensity = 900
        keyLight.position = SCNVector3(-160,280,450); scene!.rootNode.addChildNode(keyLight)
        let fill = SCNNode(); fill.light = SCNLight(); fill.light!.type = .ambient; fill.light!.intensity = 250; scene!.rootNode.addChildNode(fill)

        text("historyRole","TRACE · 실행 기록",at:SCNVector3(-340,-204,-61),width:255,height:28,size:13)
        for i in 0..<4 {
            text("event\(i)","",at:SCNVector3(-340+CGFloat(i)*174,-238,-61),width:162,height:32,size:13,command:"event:\(i)")
        }
        text("history","실행한 동작이 여기에 쌓입니다",at:SCNVector3(-65,-204,-61),width:405,height:28,size:13,color:secondary,command:"history")
        module("history",rect:CGRect(x:-358,y:-246,width:720,height:76),depth:-65,keys:["historyRole","history","event0","event1","event2","event3"])
        text("status","요청을 기다리고 있어요",at:SCNVector3(-440,-268,12),width:610,height:30,size:13)
        text("run","요청하기 ⌘↵",at:SCNVector3(288,-268,32),width:180,height:30,size:15,color:accent,command:"run")
        text("pause","일시정지",at:SCNVector3(-440,-305,12),width:120,height:32,size:13,color:accent,command:"pause")
        text("stop","중지",at:SCNVector3(-290,-305,12),width:80,height:32,size:13,color:accent,command:"stop")
        text("report","작업 기록",at:SCNVector3(-165,-305,12),width:120,height:32,size:13,color:accent,command:"report")
        text("left","↶ 시점",at:SCNVector3(70,-305,12),width:95,height:32,size:13,color:accent,command:"left")
        text("right","시점 ↷",at:SCNVector3(190,-305,12),width:95,height:32,size:13,color:accent,command:"right")
        text("home","전체 보기",at:SCNVector3(346,-305,12),width:120,height:32,size:13,color:accent,command:"home")
        for key in ["request","source","result","history"] { let route = SCNNode(); world.addChildNode(route); routes[key] = route }
        // A rear plane gives camera parallax a stable spatial reference.
        for i in -5...5 {
            let line = SCNNode(geometry:SCNBox(width:1000,height:0.5,length:0.5,chamferRadius:0))
            line.position = SCNVector3(0,-140+Double(i)*45,-150); line.eulerAngles.x = -0.18
            world.addChildNode(line); surfaces.append((line,"grid"))
        }
    }
    override func viewDidChangeEffectiveAppearance() { super.viewDidChangeEffectiveAppearance(); updateAppearance() }
    private func updateAppearance() {
        sceneDirty = true
        effectiveAppearance.performAsCurrentDrawingAppearance {
            let dark = effectiveAppearance.bestMatch(from:[.darkAqua,.aqua]) == .darkAqua
            ink = dark ? NSColor(red:0.92,green:0.96,blue:0.94,alpha:1) : NSColor(red:0.08,green:0.16,blue:0.18,alpha:1)
            secondary = dark ? NSColor(red:0.70,green:0.82,blue:0.82,alpha:1) : NSColor(red:0.29,green:0.39,blue:0.40,alpha:1)
            outline = dark ? NSColor(red:0.43,green:0.68,blue:0.69,alpha:1) : NSColor(red:0.10,green:0.23,blue:0.25,alpha:1)
            accent = dark ? NSColor(red:0.28,green:0.84,blue:0.89,alpha:1) : NSColor(red:0.02,green:0.45,blue:0.52,alpha:1)
            backgroundColor = dark ? NSColor(red:0.035,green:0.066,blue:0.083,alpha:1) : NSColor(red:0.94,green:0.95,blue:0.91,alpha:1)
            for (node,role) in surfaces {
                let color:NSColor
                switch role {
                case "panel": color = dark ? NSColor(red:0.07,green:0.12,blue:0.15,alpha:1) : NSColor(red:1.0,green:0.99,blue:0.95,alpha:1)
                case "paper": color = dark ? NSColor(red:0.10,green:0.17,blue:0.20,alpha:1) : NSColor(red:0.78,green:0.86,blue:0.80,alpha:1)
                case "shell": color = dark ? NSColor(red:0.08,green:0.25,blue:0.29,alpha:1) : NSColor(red:0.43,green:0.83,blue:0.79,alpha:1)
                case "energy", "nucleus": color = accent
                case "shadow": color = dark ? NSColor(red:0.01,green:0.035,blue:0.05,alpha:1) : NSColor(red:0.67,green:0.75,blue:0.70,alpha:1)
                case "outline", "border": color = outline
                case "grid": color = outline.withAlphaComponent(0.06)
                default: color = outline.withAlphaComponent(0.5)
                }
                let m = ["shell","nucleus"].contains(role) ? toonMaterial(color) : material(color)
                if role == "outline" { m.isDoubleSided = false; m.cullMode = .front }
                node.geometry?.materials = [m]
            }
            for (key,node) in textNodes {
                let colored = ["brand","coreTitle","sourceTitle","resultTitle","sourceNext","resultNext","sourceFull","resultFull","run","pause","stop","report","left","right","home"].contains(key)
                let primary = ["source","result","status","sourceRole","resultRole","historyRole","requestTitle"].contains(key)
                node.color = colored ? accent : (primary ? ink : secondary); node.redraw()
            }
        }
    }
    private func set(_ key:String,_ value:String) {
        sceneDirty = true
        if let node = textNodes[key], node.value != value { node.value = value; node.redraw() }
        targets.first { $0.0 == key }?.3.setAccessibilityLabel(value)
    }
    static func textAttributes(font:NSFont,color:NSColor = .labelColor,body:Bool = true) -> [NSAttributedString.Key:Any] {
        let paragraph = NSMutableParagraphStyle()
        paragraph.lineBreakMode = .byWordWrapping
        paragraph.minimumLineHeight = ceil(font.ascender-font.descender+font.leading+2)
        paragraph.maximumLineHeight = paragraph.minimumLineHeight
        return [.font:font,.foregroundColor:color,.paragraphStyle:paragraph]
    }
    static func textLayout(_ value:String,font:NSFont,color:NSColor = .labelColor,size:CGSize,body:Bool = true) -> (NSTextStorage,NSLayoutManager,NSTextContainer) {
        let storage = NSTextStorage(string:value,attributes:textAttributes(font:font,color:color,body:body))
        let layout = NSLayoutManager(); let container = NSTextContainer(containerSize:size)
        container.lineFragmentPadding = 0
        container.lineBreakMode = body ? .byWordWrapping : .byTruncatingTail
        if !body { container.maximumNumberOfLines = max(1,Int(size.height/ceil(font.ascender-font.descender+font.leading+2))) }
        layout.addTextContainer(container); storage.addLayoutManager(layout)
        layout.ensureLayout(for:container)
        return (storage,layout,container)
    }
    /// Measure with the renderer's exact font and paragraph metrics.
    static func pages(_ text:String,width:CGFloat = 295,height:CGFloat = 195,font:NSFont = .systemFont(ofSize:19,weight:.medium)) -> [String] {
        guard !text.isEmpty else { return [] }
        var pages = [String](), current = ""
        for char in text {
            let next = current + String(char)
            let (storage,layout,container) = textLayout(next,font:font,size:CGSize(width:width,height:height-2))
            let fits = layout.glyphRange(for:container).length == layout.numberOfGlyphs
            withExtendedLifetime(storage) {}
            if !fits && !current.isEmpty { pages.append(current); current = String(char) }
            else { current = next }
        }
        if !current.isEmpty { pages.append(current) }; return pages
    }
    private func updateTypography() {
        guard bounds.height > 0 else { return }
        let aspect = max(0.4,bounds.width/bounds.height)
        let z = max(960,590/tan(21 * Double.pi/180)/aspect)
        // Reserve the far plane, focus travel and maximum supported yaw.
        let projection = bounds.height/2/tan(21 * Double.pi/180)/(z+160)*cos(0.24)
        let sourceOffset = sourcePages.prefix(sourcePage).reduce(0) { $0+$1.count }
        let resultOffset = resultPages.prefix(resultPage).reduce(0) { $0+$1.count }
        var repaginate = false
        for (key,node) in textNodes {
            let minimum:CGFloat = ["sourceTitle","resultTitle"].contains(key) ? 16 : node.body ? 15 : node.name != nil ? 13 : 12
            let size = ceil(max(node.baseSize,minimum/max(0.1,projection))*2)/2
            if node.font.pointSize != size {
                node.font = .systemFont(ofSize:size,weight:node.weight); node.redraw()
                if node.body { readingFont = node.font; repaginate = true }
            }
        }
        if repaginate {
            sourcePages = Self.pages(state.source,font:readingFont); resultPages = Self.pages(state.result,font:readingFont)
            func page(at offset:Int,in pages:[String]) -> Int {
                var start = 0
                for (i,page) in pages.enumerated() { if start+page.count > offset { return i }; start += page.count }
                return max(0,pages.count-1)
            }
            sourcePage = page(at:sourceOffset,in:sourcePages); resultPage = page(at:resultOffset,in:resultPages); renderState()
        }
    }
    func update(_ next:RunPresentationState) {
        if next.runID != state.runID {
            queued = []; transfers.forEach { $0.0.removeFromParentNode() }; transfers = []
            sourcePage = 0; resultPage = 0; historyPage = 0; resultRevealAt = nil; motion = SpatialMotion(); selected = ""; linked = false; orbitTime = 0
        }
        if motion.frozen && next.runID == state.runID { queued.append(next); return }
        apply(next)
    }
    private func apply(_ next:RunPresentationState) {
        let sourceChanged = next.source != state.source && !next.source.isEmpty
        let resultChanged = next.result != state.result && !next.result.isEmpty
        if next.history.count > state.history.count { historyPage = max(0,next.history.count-1) }
        state = next
        if sourceChanged { sourcePages = Self.pages(next.source,font:readingFont); sourcePage = 0; transfer(String(next.source.prefix(42)),reverse:false,source:true) }
        if resultChanged {
            resultPages = Self.pages(next.result,font:readingFont); resultPage = 0
            resultRevealAt = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion ? nil : motion.time+1.5
            transfer(String(next.result.prefix(42)),reverse:false,source:false)
        }
        if next.source.isEmpty { sourcePages = [] }; if next.result.isEmpty { resultPages = [] }
        renderState()
    }
    func execution(active:Bool,pauseRequested:Bool,paused:Bool) {
        self.active = active; pendingPause = pauseRequested; self.paused = paused
        let frozen = active && pauseRequested
        if motion.frozen && !frozen {
            motion.frozen = false
            let pending = queued; queued = []; for snapshot in pending { apply(snapshot) }
        }
        motion.frozen = frozen
        renderControls()
        set("coreLabel",pendingPause ? "일시 정지" : active ? "실행 중" : state.outcome == nil ? "요청 대기" : "실행 종료 · 기록 보존")
    }
    func message(_ text:String) { set("status",text) }
    private func renderState() {
        set("target",state.target.isEmpty ? "맡길 일을 입력해 주세요" : targetTitle(state.target))
        set("request",state.request.isEmpty ? "목표와 작업 범위" : state.request)
        set("resultRole",state.result.isEmpty ? "OUTPUT · 결과 / 응답 대기" : "OUTPUT · 결과 / 응답 도착")
        for i in 0..<4 {
            let start = max(0,state.history.count-4), index = start+i
            set("event\(i)",index < state.history.count ? "\(index+1) · " + state.history[index] : "")
        }
        set("sourceTitle",state.sourceTitle.isEmpty ? "원문" : state.sourceTitle)
        set("source",sourcePages.isEmpty ? "원문이 필요한 요청이면\n확인한 문서가 여기에 나타납니다." : sourcePages[min(sourcePage,sourcePages.count-1)])
        set("result",resultRevealAt != nil ? "결과를 이 공간으로 옮기고 있어요" : (resultPages.isEmpty ? (state.outcome == nil ? "실행 결과를 기다리고 있습니다." : state.phase) : resultPages[min(resultPage,resultPages.count-1)]))
        set("sourcePage",sourcePages.isEmpty ? "" : "\(sourcePage+1) / \(sourcePages.count) · 원문 전체 보존")
        set("resultPage",resultPages.isEmpty ? "" : "\(resultPage+1) / \(resultPages.count)")
        set("provenance",state.hasDocumentProvenance ? "문서 전체 ↔ 결과\n눌러서 연결 따라가기" : "")
        if !state.history.isEmpty { set("history",state.history[min(historyPage,state.history.count-1)] + "  ·  \(min(historyPage+1,state.history.count))/\(state.history.count)") }
        else { set("history","실행한 동작이 여기에 쌓입니다") }
        set("coreLabel",pendingPause ? "일시 정지" : state.outcome == nil ? (active ? "실행 중" : "요청 대기") : "실행 종료 · 기록 보존")
        renderControls()
    }
    private func targetTitle(_ value:String) -> String {
        guard !value.contains(" · ") else { return value }
        return value.components(separatedBy:", ").map { bundle in
            if let name = NSRunningApplication.runningApplications(withBundleIdentifier:bundle).first?.localizedName { return name }
            if let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier:bundle), let info = Bundle(url:url) {
                return (info.object(forInfoDictionaryKey:"CFBundleDisplayName") as? String) ?? (info.object(forInfoDictionaryKey:"CFBundleName") as? String) ?? bundle
            }
            return bundle
        }.joined(separator:", ")
    }
    private func renderControls() {
        set("status",pendingPause ? (paused ? "일시정지했어요 · 같은 작업을 이어갈 수 있어요" : "진행 중인 작업이 끝나면 일시정지해요") : state.phase)
        set("run",active ? "진행 중" : "요청하기 ⌘↵")
        set("pause",pendingPause ? "계속하기" : "일시정지")
        for key in ["pause","stop"] { textNodes[key]?.opacity = active ? 1 : 0.82; targets.first { $0.0 == key }?.3.setAccessibilityEnabled(active) }
        targets.first { $0.0 == "run" }?.3.setAccessibilityEnabled(!active)
        targets.first { $0.0 == "sourceFull" }?.3.setAccessibilityEnabled(!state.source.isEmpty)
        targets.first { $0.0 == "resultFull" }?.3.setAccessibilityEnabled(!state.result.isEmpty)
        for (key,enabled) in [("sourceFull",!state.source.isEmpty),("resultFull",!state.result.isEmpty),("sourceNext",sourcePages.count>1),("resultNext",resultPages.count>1),("report",state.outcome != nil)] {
            textNodes[key]?.opacity = enabled ? 1 : 0.82; targets.first { $0.0 == key }?.3.setAccessibilityEnabled(enabled)
        }
    }
    private func transfer(_ value:String,reverse:Bool,source:Bool,delay:Double = 0) {
        guard !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else { return }
        let node = SpatialTextNode((source ? "원문 · " : "결과 · ")+String(value.prefix(12)),size:CGSize(width:90,height:60),fontSize:readingFont.pointSize*0.85,weight:.medium,color:accent,body:true)
        node.name = source ? "sourceTransfer" : "resultTransfer"; world.addChildNode(node)
        node.opacity = delay > 0 ? 0 : 1
        transfers.append((node,motion.time+delay,reverse))
    }
    private func tick() {
        let now = ProcessInfo.processInfo.systemUptime; let delta = now-lastTick; lastTick = now
        guard window?.isVisible == true else { return }
        let reduced = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        let settling = motion.focus != motion.target || motion.velocity != 0 || yaw != yawTarget || pitch != pitchTarget || modules.contains { key,node in
            let depth:CGFloat = key == selected || linked && ["source","result"].contains(key) ? 22 : 0
            return CGFloat(node.position.z) != depth
        }
        let animating = active && !pendingPause && !reduced || !transfers.isEmpty || resultRevealAt != nil || settling
        guard sceneDirty || animating && !motion.frozen else { return }
        motion.advance(delta,reducedMotion:reduced)
        if !motion.frozen {
            let blend = reduced ? 1 : min(1,max(0,delta)*7)
            yaw += (yawTarget-yaw)*blend; pitch += (pitchTarget-pitch)*blend
            if abs(yawTarget-yaw) < 0.00001 { yaw = yawTarget }
            if abs(pitchTarget-pitch) < 0.00001 { pitch = pitchTarget }
            if let reveal = resultRevealAt, motion.time >= reveal || reduced { resultRevealAt = nil; renderState() }
        }
        SCNTransaction.begin(); SCNTransaction.animationDuration = 0
        let t = motion.time
        if !motion.frozen && active && !reduced { orbitTime += min(delta,0.05) }
        orbits.eulerAngles = SCNVector3(reduced ? 0 : sin(orbitTime*0.35)*0.15,reduced ? 0 : orbitTime*0.22,0)
        world.eulerAngles = SCNVector3(pitch,yaw,0)
        let aspect = max(0.4,Double(bounds.width/max(1,bounds.height)))
        let z = max(960,590 / tan(21 * Double.pi/180) / aspect)
        cameraNode.position = SCNVector3(motion.focus*55,-12,z+abs(motion.focus)*70)
        for (key,node) in modules {
            let goal:CGFloat = key == selected || linked && ["source","result"].contains(key) ? 22 : 0
            if !motion.frozen {
                let next = CGFloat(node.position.z) + (goal-CGFloat(node.position.z)) * (reduced ? 1 : min(1,delta*7))
                node.position.z = abs(next-goal) < 0.001 ? goal : next
            }
            let highlighted = key == selected || linked && ["source","result"].contains(key)
            borders[key]?.geometry?.materials = [material(highlighted ? accent : outline)]
        }
        for key in routes.keys {
            let points = (0...40).map { routePoint(key,Double($0)/40) }
            let highlighted = linked && ["source","result"].contains(key) || active && !pendingPause && ((key == "source" && !state.source.isEmpty && state.result.isEmpty) || (key == "result" && resultRevealAt != nil))
            // A ribbon has a real width in the shared 3D world, unlike a GPU hairline.
            var vertices = [SCNVector3](), indices = [Int32]()
            for (i,p) in points.enumerated() {
                let a = points[max(0,i-1)], b = points[min(points.count-1,i+1)]
                let dx = b.x-a.x, dy = b.y-a.y, length = max(0.001,sqrt(dx*dx+dy*dy))
                let halfWidth:CGFloat = highlighted ? 1.8 : 1.1
                let nx = -dy/length*halfWidth, ny = dx/length*halfWidth
                vertices.append(SCNVector3(p.x+nx,p.y+ny,p.z)); vertices.append(SCNVector3(p.x-nx,p.y-ny,p.z))
                if i < points.count-1 { let v = Int32(i*2); indices += [v,v+1,v+2,v+1,v+3,v+2] }
            }
            let geometry = SCNGeometry(sources:[SCNGeometrySource(vertices:vertices)],elements:[SCNGeometryElement(indices:indices,primitiveType:.triangles)])
            geometry.materials = [material(highlighted ? accent : outline.withAlphaComponent(0.6))]
            routes[key]?.geometry = geometry
        }
        var finished = [Int]()
        for (index,item) in transfers.enumerated() {
            if t < item.1 { item.0.opacity = 0; continue }
            let p = min(1,max(0,(t-item.1)/1.5)); let eased = p*p*(3-2*p)
            let u = item.2 ? 1-eased : eased
            let isSource = item.0.name == "sourceTransfer"
            let point = routePoint(isSource ? "source" : "result",u)
            item.0.position = SCNVector3(point.x-35,point.y+8,point.z+8)
            item.0.opacity = p > 0.88 ? (1-p)/0.12 : 1
            if p >= 1 { finished.append(index) }
        }
        for i in finished.reversed() { transfers[i].0.removeFromParentNode(); transfers.remove(at:i) }
        SCNTransaction.commit(); updateAXFrames(); sceneDirty = false
    }
    private func routePoint(_ key:String,_ u:Double) -> SCNVector3 {
        let coreZ = Double(modules["core"]?.position.z ?? 0)
        let offset = Double(modules[key]?.position.z ?? 0)
        let a:SCNVector3, b:SCNVector3
        switch key {
        case "source": a = SCNVector3(-121,35,-28+offset); b = SCNVector3(-36,35,68+coreZ)
        case "result": a = SCNVector3(76,35,68+coreZ); b = SCNVector3(154,35,32+offset)
        case "request": a = SCNVector3(20,120,-61+offset); b = SCNVector3(20,92,68+coreZ)
        default: a = SCNVector3(20,-20,68+coreZ); b = SCNVector3(20,-169,-61+offset)
        }
        return SCNVector3(Double(a.x)+Double(b.x-a.x)*u,Double(a.y)+Double(b.y-a.y)*u+sin(u*Double.pi)*(key == "source" || key == "result" ? 12 : 0),Double(a.z)+Double(b.z-a.z)*u)
    }
    override func layout() { super.layout(); updateTypography(); sceneDirty = true; updateAXFrames() }
    private func updateAXFrames() {
        guard let window else { return }
        for (_,node,size,ax) in targets {
            let corners = [SCNVector3Zero,SCNVector3(size.width,0,0),SCNVector3(0,size.height,0),SCNVector3(size.width,size.height,0)].map { projectPoint(node.convertPosition($0,to:nil)) }
            let xs = corners.map { CGFloat($0.x) }, ys = corners.map { CGFloat($0.y) }
            let rect = CGRect(x:xs.min()!,y:ys.min()!,width:xs.max()!-xs.min()!,height:ys.max()!-ys.min()!)
            ax.setAccessibilityFrame(window.convertToScreen(convert(rect,to:nil)))
        }
    }
    override func accessibilityChildren() -> [Any]? { targets.filter { ($0.1 as? SpatialTextNode)?.value.isEmpty == false }.map { $0.3 } }
    private func command(_ name:String) {
        switch name {
        case "source": if !motion.frozen { selected = "source"; linked = false; motion.target = -1 }
        case "result": if !motion.frozen { selected = "result"; linked = false; motion.target = 1 }
        case "request": if !motion.frozen { selected = "request"; linked = false; motion.target = 0 }
        case "core": if !motion.frozen { selected = "core"; linked = false; motion.target = 0 }
        case "home": if !motion.frozen { selected = ""; linked = false; motion.target = 0; yawTarget = -0.07; pitchTarget = 0.025 }
        case "left": if !motion.frozen { yawTarget = max(-0.24,yawTarget-0.06) }
        case "right": if !motion.frozen { yawTarget = min(0.24,yawTarget+0.06) }
        case "sourceNext": if !sourcePages.isEmpty && !motion.frozen { sourcePage = (sourcePage+1)%sourcePages.count; renderState() }
        case "resultNext": if !resultPages.isEmpty && !motion.frozen { resultPage = (resultPage+1)%resultPages.count; renderState() }
        case "history": if !state.history.isEmpty && !motion.frozen {
            selected = "history"; linked = false
            historyPage = (historyPage+1)%state.history.count
            motion.target = state.historyFocus[historyPage]; renderState()
        }
        case "trace":
            if state.hasDocumentProvenance && !motion.frozen {
                linked = !linked; selected = linked ? "source" : ""; motion.target = linked ? -1 : 0
                guard linked else { return }
                transfer(state.result,reverse:true,source:false)
                transfer(state.source,reverse:true,source:true,delay:1.5)
            }
        case "sourceFull": if !state.source.isEmpty { document(state.sourceTitle,text:state.source) }
        case "resultFull": if !state.result.isEmpty { document("작업 결과",text:state.result) }
        case "requestFull": if !state.request.isEmpty { document("작업 요청",text:state.request) }
        default:
            if name.hasPrefix("event:"),let slot = Int(name.dropFirst(6)), !motion.frozen {
                let index = max(0,state.history.count-4)+slot
                guard state.history.indices.contains(index) else { return }
                selected = "history"; linked = false; historyPage = index; motion.target = state.historyFocus[index]; renderState()
            } else { onCommand(name) }
        }
    }
    override func mouseDown(with event:NSEvent) {
        window?.makeFirstResponder(self)
        let point = convert(event.locationInWindow,from:nil)
        for hit in hitTest(point,options:nil) {
            var node:SCNNode? = hit.node
            while let current = node { if let name = current.name, !name.hasSuffix("Transfer") { command(name); return }; node = current.parent }
        }
        dragPoint = point
    }
    override func mouseDragged(with event:NSEvent) {
        guard let last = dragPoint, !motion.frozen else { return }; let p = convert(event.locationInWindow,from:nil)
        yawTarget = max(-0.24,min(0.24,yawTarget+Double(p.x-last.x)*0.001)); pitchTarget = max(-0.08,min(0.08,pitchTarget-Double(p.y-last.y)*0.0005)); dragPoint = p
    }
    override func mouseUp(with event:NSEvent) { dragPoint = nil }
    override func keyDown(with event:NSEvent) {
        switch event.keyCode {
        case 53: command("home")
        case 123: command("source")
        case 124: command("result")
        case 49: onCommand("pause")
        default:
            switch event.charactersIgnoringModifiers {
            case "s": command("sourceFull")
            case "r": command("resultFull")
            case "[": command("sourceNext")
            case "]": command("resultNext")
            case "h": command("history")
            default: super.keyDown(with:event)
            }
        }
    }
    private var documentWindow: NSWindow?
    private func document(_ title:String,text:String) {
        guard let parent = window else { return }
        if let existing = documentWindow { existing.makeKeyAndOrderFront(nil); return }
        let sheet = NSWindow(contentRect:NSRect(x:0,y:0,width:640,height:460),styleMask:[.titled,.resizable],backing:.buffered,defer:false)
        sheet.title = title; sheet.isReleasedWhenClosed = false
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.translatesAutoresizingMaskIntoConstraints = false
        let view = WrappingTextView(usingTextLayoutManager:false); view.isEditable = false; view.isSelectable = true; view.isRichText = false
        view.font = .systemFont(ofSize:15); view.string = text; view.textContainerInset = NSSize(width:16,height:16)
        view.isVerticallyResizable = true; view.isHorizontallyResizable = false; view.autoresizingMask = [.width]; view.setAccessibilityLabel(title)
        scroll.documentView = view
        let close = NSButton(title:"닫기",target:self,action:#selector(closeDocument)); close.keyEquivalent = "\u{1b}"; close.translatesAutoresizingMaskIntoConstraints = false
        sheet.contentView!.addSubview(scroll); sheet.contentView!.addSubview(close)
        NSLayoutConstraint.activate([scroll.leadingAnchor.constraint(equalTo:sheet.contentView!.leadingAnchor),scroll.trailingAnchor.constraint(equalTo:sheet.contentView!.trailingAnchor),scroll.topAnchor.constraint(equalTo:sheet.contentView!.topAnchor),scroll.bottomAnchor.constraint(equalTo:close.topAnchor,constant:-12),close.trailingAnchor.constraint(equalTo:sheet.contentView!.trailingAnchor,constant:-16),close.bottomAnchor.constraint(equalTo:sheet.contentView!.bottomAnchor,constant:-12)])
        documentWindow = sheet; parent.beginSheet(sheet)
    }
    @objc private func closeDocument() { if let sheet = documentWindow { window?.endSheet(sheet); sheet.orderOut(nil) }; documentWindow = nil }
}
