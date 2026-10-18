#import <UIKit/UIKit.h>
static NSMutableDictionary *state;
static void save(void) {
    NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    [[NSJSONSerialization dataWithJSONObject:state options:0 error:nil]writeToFile:[dir stringByAppendingPathComponent:@"state.json"]atomically:YES];
}
static void increment(NSString *key){state[key]=@([state[key]intValue]+1);save();}
@interface Surface:UIView <UIGestureRecognizerDelegate>
@end
@implementation Surface
-(instancetype)initWithFrame:(CGRect)frame {
    if((self=[super initWithFrame:frame])){
        self.backgroundColor=UIColor.whiteColor;self.multipleTouchEnabled=YES;
        UILabel *label=[[UILabel alloc]initWithFrame:CGRectMake(20,70,frame.size.width-40,50)];label.text=@"MacPilot owned Simulator fixture";label.accessibilityIdentifier=@"fixture-title";label.adjustsFontSizeToFitWidth=YES;[self addSubview:label];
        UIButton *b=[UIButton buttonWithType:UIButtonTypeSystem];b.frame=CGRectMake(40,160,frame.size.width-80,80);[b setTitle:@"Increment fixture counter" forState:0];b.accessibilityIdentifier=@"increment";[b addTarget:self action:@selector(tap)forControlEvents:UIControlEventTouchUpInside];[self addSubview:b];
        state[@"buttonX"]=@(CGRectGetMidX(b.frame)/frame.size.width);state[@"buttonY"]=@(CGRectGetMidY(b.frame)/frame.size.height);
        UITextField *field=[[UITextField alloc]initWithFrame:CGRectMake(40,270,frame.size.width-80,60)];field.placeholder=@"Synthetic input";field.borderStyle=UITextBorderStyleRoundedRect;field.accessibilityIdentifier=@"synthetic-text";[field addTarget:self action:@selector(text:)forControlEvents:UIControlEventEditingChanged];[self addSubview:field];
        UILongPressGestureRecognizer *longPress=[[UILongPressGestureRecognizer alloc]initWithTarget:self action:@selector(longPress:)];longPress.minimumPressDuration=0.4;longPress.delegate=self;[self addGestureRecognizer:longPress];
        UIPinchGestureRecognizer *pinch=[[UIPinchGestureRecognizer alloc]initWithTarget:self action:@selector(pinch:)];pinch.delegate=self;[self addGestureRecognizer:pinch];
    }return self;
}
-(void)tap{increment(@"clicks");}
-(void)text:(UITextField*)v{state[@"text"]=v.text?:@"";save();}
-(void)longPress:(UILongPressGestureRecognizer*)v{if(v.state==UIGestureRecognizerStateBegan)increment(@"longPresses");}
-(void)pinch:(UIPinchGestureRecognizer*)v{state[@"pinchScale"]=@(v.scale);increment(@"pinchEvents");}
-(BOOL)gestureRecognizer:(UIGestureRecognizer*)a shouldRecognizeSimultaneouslyWithGestureRecognizer:(UIGestureRecognizer*)b{return YES;}
-(void)touchesBegan:(NSSet*)touches withEvent:(UIEvent*)event{state[@"maxTouches"]=@(MAX([state[@"maxTouches"]intValue],(int)event.allTouches.count));increment(@"touchBegins");}
-(void)touchesMoved:(NSSet*)touches withEvent:(UIEvent*)event{increment(@"touchMoves");}
-(void)touchesEnded:(NSSet*)touches withEvent:(UIEvent*)event{increment(@"touchEnds");}
-(void)touchesCancelled:(NSSet*)touches withEvent:(UIEvent*)event{increment(@"touchCancels");}
@end
@interface SceneDelegate:UIResponder <UIWindowSceneDelegate>
@property(nonatomic,strong)UIWindow *window;
@end
@implementation SceneDelegate
-(void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
    CGRect bounds=((UIWindowScene*)scene).screen.bounds;
    state[@"width"]=@(bounds.size.width);state[@"height"]=@(bounds.size.height);
    self.window=[[UIWindow alloc]initWithWindowScene:(UIWindowScene*)scene];
    UIViewController *controller=[UIViewController new];controller.view=[[Surface alloc]initWithFrame:bounds];self.window.rootViewController=controller;[self.window makeKeyAndVisible];save();
}
-(void)scene:(UIScene*)scene openURLContexts:(NSSet<UIOpenURLContext*>*)contexts{state[@"lastURL"]=contexts.anyObject.URL.absoluteString?:@"";save();}
-(void)sceneWillResignActive:(UIScene*)scene{increment(@"resignActive");}
-(void)sceneDidBecomeActive:(UIScene*)scene{increment(@"becomeActive");}
@end
@interface Delegate:UIResponder <UIApplicationDelegate>
@end
@implementation Delegate
-(BOOL)application:(UIApplication*)app didFinishLaunchingWithOptions:(NSDictionary*)options {
    state=[@{@"clicks":@0,@"touchBegins":@0,@"touchMoves":@0,@"touchEnds":@0,@"touchCancels":@0,@"maxTouches":@0,@"longPresses":@0,@"pinchEvents":@0}mutableCopy];return YES;
}
-(UISceneConfiguration*)application:(UIApplication*)app configurationForConnectingSceneSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
    UISceneConfiguration *c=[[UISceneConfiguration alloc]initWithName:@"Fixture" sessionRole:session.role];c.delegateClass=SceneDelegate.class;return c;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Delegate.class));}}
