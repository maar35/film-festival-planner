using System;
using System.Linq;
using AppKit;
using CoreAnimation;
using CoreGraphics;
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
        public const float VerticalPixelsBetweenControls = 4;
        public const float VerticalPixelsBetweenLabels = 2;
        public const float VerticalPixelsBetweenViews = 12;
        public const float StandardButtonWidth = 94;
        public const float StandardButtonHeight = 32;
        public const float StandardLabelWidth = 128;
        public const float StandardLabelHeight = 19;
        public const float SmallControlWidth = 64;
        public const string EscapeKey = "\x1b";
        public const string EnterKey = "\r";
        #endregion

        #region Constructors
        static ControlsFactory()
        {
        }
        #endregion

        #region Public Methods
        public static NSTextField NewStandardLabel(CGRect frame, bool useWindowsBackgroundCoplor = false)
        {
            var label = new NSTextField(frame)
            {
                Editable = false,
                Bordered = false,
                LineBreakMode = NSLineBreakMode.TruncatingMiddle
            };
            if (useWindowsBackgroundCoplor)
            {
                label.BackgroundColor = NSColor.WindowBackground;
            }
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
            var cancelButton = ControlsFactory.NewStandardButton(frame);
            cancelButton.Title = "Cancel";
            cancelButton.KeyEquivalent = EscapeKey;
            return cancelButton;
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

        public static NSScrollView NewStandardScrollView(CGRect frame, NSView documentView, bool debug = false)
        {
            var scrollView = new NSScrollView(frame);
            scrollView.BackgroundColor = NSColor.WindowBackground;
            scrollView.BorderType = NSBorderType.BezelBorder;
            scrollView.DocumentView = documentView;
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
