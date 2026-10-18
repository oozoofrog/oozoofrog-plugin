// Optional private API driver. No host event injection and no linked Xcode frameworks.
#import <AppKit/AppKit.h>
#import <objc/message.h>
#import <dlfcn.h>
#import <libproc.h>
#import <signal.h>

static volatile sig_atomic_t stopped;
static void stop(int sig) { stopped = sig; }
static void fail(NSString *code, NSString *message) {
    @throw [NSException exceptionWithName:code reason:message userInfo:nil];
}
static id get(id obj, NSString *name) {
    SEL sel=NSSelectorFromString(name);
    if (![obj respondsToSelector:sel]) fail(@"private_api_unavailable", name);
    return ((id(*)(id,SEL))objc_msgSend)(obj,sel);
}
static double number(NSDictionary *a, NSString *key, double minimum, double maximum) {
    id v=a[key];
    if (![v isKindOfClass:NSNumber.class] || CFGetTypeID((__bridge CFTypeRef)v)==CFBooleanGetTypeID()
        || !isfinite([v doubleValue]) || [v doubleValue]<minimum || [v doubleValue]>maximum)
        fail(@"invalid_argument",key);
    return [v doubleValue];
}
static NSString *startID(pid_t pid) {
    struct proc_bsdinfo info={0};
    if(proc_pidinfo(pid, PROC_PIDTBSDINFO,0,&info,sizeof(info))!=sizeof(info)) return nil;
    return [NSString stringWithFormat:@"%llu.%llu",info.pbi_start_tvsec,info.pbi_start_tvusec];
}
typedef void *(*Mouse)(CGPoint *,CGPoint *,int,NSUInteger,NSSize,int);
typedef void *(*Button)(int,int,int);
typedef void *(*Keyboard)(unsigned,int);
static id client;
static dispatch_queue_t ackQueue;
static BOOL sent;
static void sendMessage(void *message) {
    if(!message) fail(@"private_message_failed",@"Builder returned no message");
    dispatch_semaphore_t sem=dispatch_semaphore_create(0);
    __block NSError *failure=nil;
    SEL sel=NSSelectorFromString(@"sendWithMessage:freeWhenDone:completionQueue:completion:");
    if(![client respondsToSelector:sel]) {free(message);fail(@"private_api_unavailable",@"Missing send selector");}
    sent=YES; // Ownership passes to the client, including exceptions during submission.
    ((void(*)(id,SEL,void*,BOOL,dispatch_queue_t,void(^)(NSError*)))objc_msgSend)(client,sel,message,YES,ackQueue,^(NSError *e){failure=e;dispatch_semaphore_signal(sem);});
    if(dispatch_semaphore_wait(sem,dispatch_time(DISPATCH_TIME_NOW,2*NSEC_PER_SEC))) fail(@"private_ack_timeout",@"Delivery uncertain; inspect guest before retry");
    if(failure) fail(@"private_delivery_failed",failure.localizedDescription);
}
static void pauseFor(double duration) {
    double until=NSProcessInfo.processInfo.systemUptime+duration;
    while(!stopped && NSProcessInfo.processInfo.systemUptime<until) usleep(5000);
    if(stopped) fail(@"cancelled",@"Input interrupted; release attempted");
}
int main(int argc, const char **argv) {@autoreleasepool {
    if(argc==4 && strcmp(argv[1],"--swap-bundles")==0) {
        if(argv[2][0]!='/' || argv[3][0]!='/')return 64;
        return renamex_np(argv[2],argv[3],RENAME_SWAP)==0 ? 0 : 74;
    }
    if(argc!=1)return 64;
    signal(SIGTERM,stop);signal(SIGINT,stop);
    NSDictionary *result;
    BOOL touchDown=NO,keyDown=NO,two=NO;
    Mouse mouse=NULL; Button button=NULL; Keyboard keyboard=NULL;
    CGPoint point=CGPointZero,second=CGPointZero;
    int key=0; BOOL hardware=NO;
    @try {
        NSData *raw=[NSFileHandle.fileHandleWithStandardInput readDataUpToLength:32769 error:nil];
        if(raw.length>32768)fail(@"invalid_argument",@"Input too large");
        NSDictionary *a=[NSJSONSerialization JSONObjectWithData:raw options:0 error:nil];
        if(![a isKindOfClass:NSDictionary.class])fail(@"invalid_argument",@"Expected JSON object");
        NSString *op=a[@"operation"],*developer=a[@"developerDir"],*udid=a[@"udid"];
        if(![op isKindOfClass:NSString.class] || ![developer isKindOfClass:NSString.class] || ![developer hasSuffix:@"/Contents/Developer"]
           || ![[NSUUID alloc]initWithUUIDString:udid])fail(@"invalid_argument",@"Exact Xcode developer directory and UUID required");
        BOOL probe=[op isEqual:@"probe"];
        if(!probe && (![a[@"privateAPI"]isKindOfClass:NSNumber.class] || CFGetTypeID((__bridge CFTypeRef)a[@"privateAPI"])!=CFBooleanGetTypeID() || ![a[@"privateAPI"]boolValue]))fail(@"private_api_disabled",@"Input requires privateAPI=true");
        NSArray *operations=@[@"probe",@"tap",@"long_press",@"swipe",@"drag",@"pinch",@"button",@"key"];
        if(![operations containsObject:op])fail(@"invalid_argument",@"Unknown input operation");
        BOOL isKey=[@[@"button",@"key"]containsObject:op];
        double duration=0.05;
        CGPoint end=CGPointZero,secondEnd=CGPointZero;
        if(!probe && !isKey) {
            point=CGPointMake(number(a,@"x",0,1),number(a,@"y",0,1)); end=point;
            duration=a[@"duration"]?number(a,@"duration",0.02,2):([op isEqual:@"long_press"]?0.6:0.25);
            if([@[@"swipe",@"drag",@"pinch"]containsObject:op])end=CGPointMake(number(a,@"toX",0,1),number(a,@"toY",0,1));
            two=[op isEqual:@"pinch"];
            if(two){second=CGPointMake(number(a,@"x2",0,1),number(a,@"y2",0,1));secondEnd=CGPointMake(number(a,@"toX2",0,1),number(a,@"toY2",0,1));}
        }
        if(isKey){
            hardware=[op isEqual:@"button"];
            NSDictionary *keys=hardware?@{@"home":@0,@"lock":@1}:@{@"return":@40,@"escape":@41,@"backspace":@42,@"tab":@43,@"space":@44,@"left":@80,@"right":@79,@"up":@82,@"down":@81};
            id keyName=a[@"key"]; if(![keyName isKindOfClass:NSString.class])fail(@"invalid_argument",@"Exact key name required");
            NSNumber *n=keys[keyName];if(!n)fail(@"invalid_argument",@"Unsupported exact key name");key=n.intValue;
        }
        NSString *kit=[[developer stringByDeletingLastPathComponent]stringByAppendingPathComponent:@"SharedFrameworks/SimulatorKit.framework/SimulatorKit"];
        void *core=dlopen("/Library/Developer/PrivateFrameworks/CoreSimulator.framework/CoreSimulator",RTLD_NOW|RTLD_LOCAL);
        void *lib=dlopen(kit.fileSystemRepresentation,RTLD_NOW|RTLD_LOCAL);
        if(!core||!lib)fail(@"private_api_unavailable",@"Xcode frameworks unavailable");
        mouse=(Mouse)dlsym(lib,"IndigoHIDMessageForMouseNSEvent");button=(Button)dlsym(lib,"IndigoHIDMessageForButton");keyboard=(Keyboard)dlsym(lib,"IndigoHIDMessageForKeyboardArbitrary");
        if(!mouse||!button||!keyboard)fail(@"private_api_unavailable",@"Missing Indigo builders");
        Class context=NSClassFromString(@"SimServiceContext");NSError *error=nil;
        SEL cs=NSSelectorFromString(@"sharedServiceContextForDeveloperDir:error:");
        if(![context respondsToSelector:cs])fail(@"private_api_unavailable",@"Missing CoreSimulator service");
        id service=((id(*)(id,SEL,id,NSError *__autoreleasing*))objc_msgSend)(context,cs,developer,&error);
        id set=((id(*)(id,SEL,NSError *__autoreleasing*))objc_msgSend)(service,NSSelectorFromString(@"defaultDeviceSetWithError:"),&error);
        if(!set)fail(@"private_api_unavailable",error.localizedDescription?:@"No default device set");
        id devices=get(set,@"devices"); if([devices isKindOfClass:NSDictionary.class])devices=[devices allValues];
        id device=nil;for(id d in devices)if([[get(get(d,@"UDID"),@"UUIDString") uppercaseString]isEqual:[udid uppercaseString]]){device=d;break;}
        if(!device)fail(@"simulator_not_found",@"Exact Simulator UUID not found");
        NSUInteger state=((NSUInteger(*)(id,SEL))objc_msgSend)(device,NSSelectorFromString(@"state"));
        if(state!=3)fail(@"simulator_not_booted",@"Simulator must be booted");
        if(!probe){
            pid_t pid=(pid_t)number(a,@"bootPID",1,INT_MAX);
            if(![(startID(pid)?:@"") isEqual:a[@"bootStartID"]])fail(@"stale_simulator_boot",@"Boot process changed");
        }
        Class cls=NSClassFromString(@"SimulatorKit.SimDeviceLegacyHIDClient");
        if(!cls)fail(@"private_api_unavailable",@"Missing legacy HID client");
        client=((id(*)(id,SEL,id,NSError *__autoreleasing*))objc_msgSend)([cls alloc],NSSelectorFromString(@"initWithDevice:error:"),device,&error);
        if(!client)fail(@"private_api_unavailable",error.localizedDescription?:@"HID client creation failed");
        ackQueue=dispatch_queue_create("local.macpilot.simulator-hid.ack",DISPATCH_QUEUE_SERIAL);
        if(!probe){
            if(stopped)fail(@"cancelled",@"Cancelled before input");
            if(isKey){keyDown=YES;sendMessage(hardware?button(key,1,0x33):keyboard(key,1));pauseFor(0.05);keyDown=NO;sendMessage(hardware?button(key,2,0x33):keyboard(key,2));}
            else {
                touchDown=YES;sendMessage(mouse(&point,two?&second:NULL,0x32,1,NSMakeSize(1,1),0));
                CGPoint from=point,from2=second;
                int steps=MAX(1,(int)ceil(duration*30));
                for(int i=1;i<=steps;i++){
                    pauseFor(duration/steps);double t=(double)i/steps;
                    point=CGPointMake(from.x+(end.x-from.x)*t,from.y+(end.y-from.y)*t);
                    second=CGPointMake(from2.x+(secondEnd.x-from2.x)*t,from2.y+(secondEnd.y-from2.y)*t);
                    if(!CGPointEqualToPoint(from,end)||two)sendMessage(mouse(&point,two?&second:NULL,0x32,6,NSMakeSize(1,1),0));
                }
                touchDown=NO;sendMessage(mouse(&point,two?&second:NULL,0x32,2,NSMakeSize(1,1),0));
            }
        }
        result=@{@"status":probe?@"private_driver_available":@"simulator_input_dispatched",@"dispatchAcknowledged":(probe?@NO:@YES),@"businessPostconditionVerified":@NO,@"privateAPI":@YES};
    } @catch(NSException *e){result=@{@"status":@"error",@"code":e.name?:@"private_driver_failed",@"message":e.reason?:@"Private driver exception",@"inputMayHaveOccurred":@(sent)};}
    @finally{
        @try{
            if(touchDown&&mouse)sendMessage(mouse(&point,two?&second:NULL,0x32,2,NSMakeSize(1,1),0));
            if(keyDown)sendMessage(hardware?button(key,2,0x33):keyboard(key,2));
        }@catch(NSException *e){NSMutableDictionary *r=[result mutableCopy];r[@"releaseError"]=e.name;result=r;}
    }
    NSData *out=[NSJSONSerialization dataWithJSONObject:result options:0 error:nil];
    [NSFileHandle.fileHandleWithStandardOutput writeData:out];puts("");
    return [result[@"status"]isEqual:@"error"]?1:0;
}}
