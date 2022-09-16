using System;
using System.Collections.Generic;
using AppKit;
using CoreAnimation;
using CoreGraphics;
using CoreText;

namespace PresentScreenings.TableView
{
    public static class ControlsFactory
    {
        #region Public Constants
        public const float HorizontalMargin = 20;
        public const float SmallHorizontalMargin = 5;
        public const float SmallVerticalMargin = 8;
        public const float BigVerticalMargin = 12;
        public const float HorizontalPixelsBetweenControls = 12;
        public const float HorizontalPixelsBetweenLabels = 2;
        public const float VerticalPixelsBetweenControls = 4;
        public const float VerticalPixelsBetweenLabels = 2;
        public const float VerticalPixelsBetweenViews = 12;
        public const float VerticalTextOffset = 3;
        public const float WideVerticalPixelsBetweenLabels = 8;
        public const float StandardButtonWidth = 94;
        public const float StandardButtonHeight = 32;
        public const float StandardLabelWidth = 128;
        public const float StandardLabelHeight = 19;
        public const float StandardLineHeight = 17;
        public const float LabelLineHeight = 16;
        public const float BigScreeningLabelHeight = 40;
        public const float SmallControlWidth = 64;
        public const float StandardImageSide = 48;
        public const float StandardButtonImageSide = 20;
        public const float StandardImageButtonWidth = 47;
        public const float SubsectionLabelWidth = 72;
        public const float ClickpadMinSideToDrawAllElements = 32;
        public const float ClickpadRightMargin = 16;
        public const float ClickpadTopMargin = 1;
        public const string EscapeKey = "\x1b";
        public const string EnterKey = "\r";
        #endregion

        #region Properties
        public static string AutomaticallyPlannedSymbol => "𝛑"; // MATHEMATICAL BOLD SMALL PI = 𝛑
        public static string ReloadButtonToolTip => "Reload ratings";
        public static nfloat StandardFontSize => NSFont.SystemFontSize;
        public static NSFont StandardFont => NSFont.SystemFontOfSize(StandardFontSize);
        public static NSFont StandardBoldFont => NSFont.BoldSystemFontOfSize(StandardFontSize);
        public static CTFont StandardCtFont => new CTFont(".AppleSytemUIFont", 14);
        public static CTFont StandardCtBoldFont => new CTFont(".AppleSystemUIFontBold", StandardFontSize);
        public static Dictionary<bool, string> TitleByChanged { get; private set; }
        public static Dictionary<ScreeningInfo.Warning, string> StringByWarning { get; private set; }
        #endregion

        #region Constructors
        static ControlsFactory()
        {
            TitleByChanged = new Dictionary<bool, string> { };
            TitleByChanged.Add(false, "Close");
            TitleByChanged.Add(true, "Save");
            StringByWarning = new Dictionary<ScreeningInfo.Warning, string> { };
            StringByWarning.Add(ScreeningInfo.Warning.NoWarning, "No warning");
            StringByWarning.Add(ScreeningInfo.Warning.SameMovie, "Attending the same film more than once");
            StringByWarning.Add(ScreeningInfo.Warning.TimeOverlap, "Overlap with an attended screening");
            StringByWarning.Add(ScreeningInfo.Warning.Unavailable, $"{ScreeningInfo.Me} is not available this day");
        }
        #endregion

        #region Public Methods that deliver controls.
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

        public static NSTextField NewScreeningWarningLabel(CGRect frame, Screening screening)
        {
            var label = NewStandardLabel(frame);
            label.Font = StandardFont;
            label.Alignment = NSTextAlignment.Center;
            label.Bordered = false;
            UpdateScreeningWarningLabel(label, screening);

            return label;
        }

        public static NSImageView NewWarningImageView(CGRect frame)
        {
            var imageView = new NSImageView(frame);
            var warningImage = NSImage.ImageNamed("NSCaution");
            imageView.Image = warningImage;
            imageView.ImageScaling = NSImageScale.ProportionallyUpOrDown;

            return imageView;
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

        public static NSButton NewVisitWebsiteButton(CGPoint origin, Film film)
        {
            return NewVisitWebsiteButton((float)origin.X, (float)origin.Y, film);
        }

        public static NSButton NewCheckbox(CGRect frame)
        {
            var box = NewStandardButton(frame);
            box.SetButtonType(NSButtonType.Switch);
            return box;
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

        #region Public Methods that handle strings.
        public static string GlobalWarningsString(int warningCount)
        {
            string warningString = CountString(warningCount, "Warning");
            return warningString;
        }

        public static string TicketProblemsString(int toBuyTicketsCount, int toSellTicketsCount)
        {
            string problemString;
            if (toBuyTicketsCount > 0 && toSellTicketsCount == 0)
            {
                problemString = CountString(toBuyTicketsCount, "screening") + " must be bought";
            }
            else if (toBuyTicketsCount == 0 && toSellTicketsCount > 0)
            {
                problemString = CountString(toSellTicketsCount, "screening") + " must be sold";
            }
            else if (toBuyTicketsCount > 0 && toSellTicketsCount > 0)
            {
                string sellString = CountString(toSellTicketsCount, "screening");
                problemString = $"Sell {sellString}, buy {toBuyTicketsCount}";
            }
            else
            {
                problemString = "No ticket problems";
            }
            return problemString;
        }

        public static string CountString(int count, string word)
        {
            string pluralString = count == 1 ? string.Empty : "s";
            string countString = count == 0 ? "No" : count.ToString();
            string countWithWordString = $"{countString} {word}{pluralString}";
            return countWithWordString;
        }

        public static string ScreeningWarningString(Screening screening)
        {
            return StringByWarning[screening.Warning];
        }

        public static void UpdateScreeningWarningLabel(NSTextField label, Screening screening)
        {
            if (screening.Warning == ScreeningInfo.Warning.NoWarning)
            {
                label.StringValue = string.Empty;
                label.BackgroundColor = NSColor.WindowBackground;
                label.TextColor = NSColor.Black;
            }
            else
            {
                label.StringValue = ScreeningWarningString(screening);
                label.BackgroundColor = ColorView.WarningBackgroundColor;
                label.TextColor = NSColor.Black;
            }
        }

        public static void UpdateWarningImage(NSView superView, NSImageView imageView, Screening screening)
        {
            if (screening.Warning == ScreeningInfo.Warning.NoWarning)
            {
                if (imageView.Superview != null)
                {
                    imageView.RemoveFromSuperview();
                }
            }
            else
            {
                if (imageView.Superview == null)
                {
                    superView.AddSubview(imageView);
                }
            }
        }

        public static string VisitWebsiteButtonToolTip(Film film)
        {
            return $"Visit the web site of {film}";
        }

        public static string FilmInfoButtonToolTip(Film film)
        {
            return $"Get more info of {film}";
        }
        #endregion
    }
}
