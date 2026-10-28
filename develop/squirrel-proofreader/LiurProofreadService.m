#import "LiurProofreadService.h"
#import <unistd.h>

@implementation LiurProofreadService {
  NSString* _bundlePath;
  NSString* _socketPath;
  NSTask* _task;
  NSTimer* _timer;
  id _terminationObserver;
  NSTimeInterval _lastStart;
  BOOL _stopped;
}
+ (instancetype)shared {
  static LiurProofreadService* service;
  static dispatch_once_t once;
  dispatch_once(&once, ^{ service = [[self alloc] init]; });
  return service;
}
- (instancetype)init {
  return [self initWithBundlePath:NSBundle.mainBundle.bundlePath
      socketPath:[@"~/Library/Rime/proofreader/run/builtin.sock" stringByExpandingTildeInPath]];
}
- (instancetype)initWithBundlePath:(NSString*)bundlePath socketPath:(NSString*)socketPath {
  if ((self = [super init])) {
    _bundlePath = [bundlePath copy];
    _socketPath = [socketPath copy];
  }
  return self;
}
- (void)start {
  if (_timer) return;
  _stopped = NO;
  NSString* contents = _bundlePath;
  NSString* client = [contents stringByAppendingPathComponent:@"Contents/Helpers/liur_proofread_client"];
  NSString* socket = _socketPath;
  setenv("LIUR_PROOFREADER_CLIENT", client.UTF8String, 1);
  setenv("LIUR_PROOFREADER_SOCKET", socket.UTF8String, 1);
  [self launchIfNeeded];
  __weak typeof(self) weakSelf = self;
  _timer = [NSTimer scheduledTimerWithTimeInterval:2 repeats:YES block:^(NSTimer* timer) {
    [weakSelf launchIfNeeded];
  }];
  _terminationObserver = [NSNotificationCenter.defaultCenter
      addObserverForName:NSApplicationWillTerminateNotification object:nil queue:nil
      usingBlock:^(NSNotification* note) { [weakSelf stop]; }];
}
- (void)launchIfNeeded {
  if (_stopped || _task.running) return;
  NSTimeInterval now = NSProcessInfo.processInfo.systemUptime;
  if (_lastStart && now - _lastStart < 10) return;
  _lastStart = now;
  NSString* root = _bundlePath;
  NSString* data = [root stringByAppendingPathComponent:@"Contents/SharedSupport/proofreader"];
  NSTask* task = [[NSTask alloc] init];
  task.executableURL = [NSURL fileURLWithPath:[root stringByAppendingPathComponent:
      @"Contents/Resources/LiurChecker/LiurChecker"]];
  task.arguments = @[@"--model-dir", [data stringByAppendingPathComponent:@"model"],
      @"--rime-dir", data, @"--socket", @(getenv("LIUR_PROOFREADER_SOCKET")),
      @"--parent-pid", [NSString stringWithFormat:@"%d", getpid()]];
  task.environment = @{@"PATH": @"/usr/bin:/bin", @"HOME": NSHomeDirectory(),
      @"OMP_NUM_THREADS": @"1"};
  task.qualityOfService = NSQualityOfServiceUserInitiated;
  task.standardOutput = NSFileHandle.fileHandleWithNullDevice;
  task.standardError = NSFileHandle.fileHandleWithNullDevice;
  NSError* error;
  if ([task launchAndReturnError:&error]) _task = task;
  else NSLog(@"Built-in proofreader could not start (code %ld)", (long)error.code);
}
- (void)stop {
  _stopped = YES;
  [_timer invalidate];
  _timer = nil;
  if (_terminationObserver) {
    [NSNotificationCenter.defaultCenter removeObserver:_terminationObserver];
    _terminationObserver = nil;
  }
  if (_task.running) [_task terminate];
  _task = nil;
}
@end
