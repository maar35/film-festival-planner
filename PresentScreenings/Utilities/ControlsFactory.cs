using System;
using System.Linq;
using AppKit;
using CoreAnimation;
using CoreGraphics;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    public static class ControlsFactory
    {
        #region Public Constants
        public const float HorizontalMargin = 20;
        public const float SmallVerticalMargin = 8;
        public const float BigVerticalMargin = 12;
        public const float HorizontalPixelsBetweenControls = 12;
        public const float HorizontalPixelsBetweenLabels = 2;
        public const float VerticalPixelsBetweenControls = 4;
        public const float VerticalPixelsBetweenLabels = 2;
        public const float VerticalPixelsBetweenViews = 12;
        public const float StandardButtonWidth = 94;
        public const float StandardButtonHeight = 32;
        public const float StandardLabelWidth = 128;
        public const float StandardLabelHeight = 19;
        public const float StandardLineHeight = 17;
        public const float SmallControlWidth = 64;
        public const float StandardButtonImageSide = 20;
        public const float StandardImageButtonWidth = 47;
        public const float SubsectionLabelWidth = 72;
        public const string EscapeKey = "\x1b";
        public const string EnterKey = "\r";
        #endregion

        #region Properties
        public static nfloat StandardFontSize => NSFont.SystemFontSize;
        public static NSFont StandardFont => NSFont.SystemFontOfSize(StandardFontSize);
        public static NSFont StandardBoldFont => NSFont.BoldSystemFontOfSize(StandardFontSize);
        public static CTFont StandardCtFont = new CTFont(".AppleSytemUIFont", 14);
        public static CTFont StandardCtBoldFont => new CTFont(".AppleSystemUIFontBold", StandardFontSize);
        #endregion

        #region Constructors
        static ControlsFactory()
        {
        }
        #endregion

        #region Public Methods
        public static NSTextField NewStandardLabel(CGRect frame, bool useWindowBackgroundColor = false)
        {
            var label = new NSTextField(frame)
            {
                Editable = false,
                Bordered = false,
                LineBreakMode = NSLineBreakMode.TruncatingMiddle
            };
            if (useWindowBackgroundColor)
            {
                label.BackgroundColor = NSColor.WindowBackground;
            }
            return label;
        }

        public static NSTextField NewSubsectionLabel(CGRect frame, Film film, bool useWindowBackgroundColor = false)
        {
            var label = NewStandardLabel(frame, useWindowBackgroundColor);
            label.StringValue = film.SubsectionName;
            label.Font = StandardFont;
            label.Alignment = NSTextAlignment.Center;
            label.LineBreakMode = NSLineBreakMode.TruncatingTail;
            label.TextColor = film.SubsectionColor;
            label.ToolTip = film.SubsectionDescription;
            label.Bordered = true;

            return label;
        }

        public static NSButton NewStandardButton(CGRect frame)
        {
            var button = new NSButton(frame)
            {
                BezelStyle = NSBezelStyle.Rounded,
                Enabled = true
            };
            button.SetButtonType(NSButtonType.MomentaryPushIn);
            return button;
        }

        public static NSButton NewCancelButton(CGRect frame)
        {
            var cancelButton = NewStandardButton(frame);
            cancelButton.Title = "Cancel";
            cancelButton.KeyEquivalent = EscapeKey;
            return cancelButton;
        }

        public static NSButton NewVisitWebsiteButton(float x, float y, Film film)
        {
            CGRect websiteButtonRect = new CGRect(x, y, StandardImageButtonWidth, StandardButtonHeight);
            NSButton websiteButton = NewStandardButton(websiteButtonRect);
            websiteButton.Image = NSImage.ImageNamed("NSNetwork");
            websiteButton.Image.Size = new CGSize(StandardButtonImageSide, StandardButtonImageSide);
            websiteButton.Action = new ObjCRuntime.Selector("VisitFilmWebsite:");
            websiteButton.ToolTip = VisitWebsiteButtonToolTip(film);
            return websiteButton;
        }

        public static NSButton NewVisitWebsiteButton(nfloat x, nfloat y, Film film)
        {
            return NewVisitWebsiteButton((float)x, (float)y, film);
        }

        public static string VisitWebsiteButtonToolTip(Film film)
        {
            return $"Visit the web site of {film}";
        }

        public static NSButton NewCheckbox(CGRect frame)
        {
            var box = NewStandardButton(frame);
            box.SetButtonType(NSButtonType.Switch);
            return box;
        }

        public static NSComboBox NewRatingComboBox(CGRect frame, NSFont font)
        {
            var comboBox = new NSComboBox(frame);
            comboBox.Add(FilmRating.Values.Select(str => new NSString(str)).ToArray());
            comboBox.Alignment = NSTextAlignment.Right;
            comboBox.Font = font;
            comboBox.AutoresizesSubviews = true;
            return comboBox;
        }

        public static NSScrollView NewStandardScrollView(CGRect frame, NSView documentView, bool useWindowBackgroundColor = false, bool debug = false)
        {
            var scrollView = new NSScrollView(frame);
            scrollView.BorderType = NSBorderType.BezelBorder;
            scrollView.DocumentView = documentView;
            if (useWindowBackgroundColor)
            {
                scrollView.BackgroundColor = NSColor.WindowBackground;
            }
            if (frame.Width > documentView.Frame.Width)
            {
                documentView.SetFrameSize(new CGSize(frame.Width, documentView.Frame.Height));
            }
            if (frame.Height > documentView.Frame.Height)
            {
                documentView.SetFrameSize(new CGSize(documentView.Frame.Width, frame.Height));
            }
            scrollView.ContentView.ScrollToPoint(new CGPoint(0, documentView.Frame.Height));

            // Set some coloring to ease debugging.
            if (debug)
            {
                CAGradientLayer gradient = new CAGradientLayer();
                CGColor[] colors = { NSColor.Blue.ColorWithAlphaComponent((nfloat)0.2).CGColor,
                                     NSColor.Blue.ColorWithAlphaComponent((nfloat)0.4).CGColor };
                gradient.Colors = colors;
                gradient.Frame = documentView.Frame;
                documentView.WantsLayer = true;
                documentView.Layer?.AddSublayer(gradient);
            }

            return scrollView;
        }
        #endregion
    }
}
