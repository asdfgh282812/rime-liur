#import "LiurProofreadHint.h"

static void check(BOOL condition, NSString* reason) {
  if (!condition) {
    NSLog(@"FAIL: %@", reason);
    exit(1);
  }
}

int main(void) {
  @autoreleasepool {
    check(LiurIsProofreadComment(@"建議「註」：備註〔Tab採用〕"), @"suggestion comment");
    check(!LiurIsProofreadComment(@""), @"empty comment");
    check(!LiurIsProofreadComment(@"ㄊㄚ"), @"ordinary comment");
    check(!LiurIsProofreadComment(@"建議「註」：備註"), @"missing Tab marker");
    check(!LiurIsProofreadComment(@"〔Tab採用〕"), @"missing suggestion text");
    check(!LiurIsProofreadComment(nil), @"nil comment");

    NSColor* red = LiurProofreadWarningColor();
    check(red.redComponent > 0.8 && red.greenComponent < 0.2 && red.blueComponent < 0.25,
          @"warning color is red");

    NSDictionary* theme = @{NSForegroundColorAttributeName: NSColor.blackColor,
                            NSFontAttributeName: [NSFont systemFontOfSize:20]};
    NSDictionary* warning = LiurProofreadWarningAttrs(theme);
    check([warning[NSForegroundColorAttributeName] isEqual:NSColor.whiteColor],
          @"white text on the red highlight");
    check([warning[NSFontAttributeName] isEqual:theme[NSFontAttributeName]], @"font kept");
    check([theme[NSForegroundColorAttributeName] isEqual:NSColor.blackColor],
          @"theme attributes are not mutated");
    puts("PASS: suggestion comment detection, red warning color and white text attributes");
  }
  return 0;
}
