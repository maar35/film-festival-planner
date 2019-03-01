using System;
using System.Linq;
using AppKit;
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
        public const float StandardLabelHeight = 19;
        public const string EscapeKey = "\x1b";
        public const string EnterKey = "\r";
        #endregion

        #region Constructors
        static ControlsFactory()
        {
        }
        #endregion

        #region Public Methods
        public static NSTextField CreateStandardLabel(CGRect frame)
        {
            var label = new NSTextField(frame)
            {
                Editable = false,
                BackgroundColor = NSColor.WindowBackground,
                Bordered = false,
                LineBreakMode = NSLineBreakMode.TruncatingMiddle
            };
            return label;
        }

        public static NSButton CreateStandardButton(CGRect frame)
        {
            var button = new NSButton(frame)
            {
                BezelStyle = NSBezelStyle.Rounded,
                Enabled = true
            };
            button.SetButtonType(NSButtonType.MomentaryPushIn);
            return button;
        }

        public static NSButton CreateCancelButton(CGRect frame)
        {
            var cancelButton = ControlsFactory.CreateStandardButton(frame);
            cancelButton.Title = "Cancel";
            cancelButton.KeyEquivalent = EscapeKey;
            return cancelButton;
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

        public static NSScrollView CreateStandardScrollView(CGRect frame, NSView documentView)
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
            return scrollView;
        }
        #endregion
    }
}
