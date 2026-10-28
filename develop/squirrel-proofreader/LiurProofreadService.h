#import <Cocoa/Cocoa.h>
@interface LiurProofreadService : NSObject
+ (instancetype)shared;
- (instancetype)initWithBundlePath:(NSString*)bundlePath socketPath:(NSString*)socketPath;
- (void)start;
- (void)stop;
@end
