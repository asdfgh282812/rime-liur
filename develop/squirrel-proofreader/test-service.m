#import "LiurProofreadService.h"
#import <signal.h>
#import <unistd.h>
static void spin(NSTimeInterval seconds) {
  [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:seconds]];
}
int main(int argc, char** argv) {
  @autoreleasepool {
    NSCAssert(argc == 3, @"app path and scratch socket required");
    LiurProofreadService* service = [[LiurProofreadService alloc]
        initWithBundlePath:@(argv[1]) socketPath:@(argv[2])];
    [service start];
    NSTask* first = [service valueForKey:@"task"];
    NSCAssert(first.running, @"helper should start");
    for (int i=0; i<100 && ![NSFileManager.defaultManager fileExistsAtPath:@(argv[2])]; ++i) spin(0.1);
    NSCAssert([NSFileManager.defaultManager fileExistsAtPath:@(argv[2])], @"helper socket ready");
    kill(first.processIdentifier, SIGKILL);
    spin(12.5);
    NSTask* second = [service valueForKey:@"task"];
    NSCAssert(second.running && second != first, @"helper should restart after crash");
    if (getenv("LIUR_TEST_ABANDON_PARENT")) _exit(0);
    [service stop];
    for (int i=0; i<30 && second.running; ++i) spin(0.1);
    NSCAssert(!second.running, @"helper should stop with app");
    NSLog(@"PASS: start, ready, crash recovery, shutdown");
  }
}
