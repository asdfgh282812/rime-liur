// Local Squirrel 0.18 extension. The text and Tab action remain owned by Lua.
#import <Cocoa/Cocoa.h>

// Lua marks a suggestion with: 建議「字」：詞〔Tab採用〕
static inline BOOL LiurIsProofreadComment(NSString* comment) {
  return [comment containsString:@"建議「"] && [comment hasSuffix:@"〔Tab採用〕"];
}

static inline NSColor* LiurProofreadWarningColor(void) {
  return [NSColor colorWithSRGBRed:0.86 green:0.15 blue:0.18 alpha:1.0];
}

// White text keeps the selected candidate readable on the red highlight, whatever
// the theme's own highlighted text color is.
static inline NSDictionary* LiurProofreadWarningAttrs(NSDictionary* attrs) {
  NSMutableDictionary* warning = [attrs mutableCopy];
  warning[NSForegroundColorAttributeName] = NSColor.whiteColor;
  return warning;
}
