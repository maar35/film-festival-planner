using System;
using AppKit;
using CoreGraphics;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Subsection control, control to represent the subsection of a film in the
    /// film rating dialog.
    /// An action on the Film property is injected in the constructor. No event
    /// is used when the control is activated in order to prevent memory leaks.
    /// </summary>

    public class SubsectionControl : NSControl
    {
        #region Private Constants
        private const float _horizontalTextOffset = 2;
        private const float _verticalTextOffset = 4;
        private NSTrackingArea _hoverArea;
        private NSCursor _cursor;
        #endregion

        #region Properties
        public Film Film { get; set; }
        public Action<Film> FilmAction { get; private set; }
        #endregion

        #region Constructors
        public SubsectionControl(CGRect frame, Film film, Action<Film> action) : base(frame)
        {
            // Initialize control features.
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;

            // Initialize mouse hovering.
            _hoverArea = new NSTrackingArea(Frame, NSTrackingAreaOptions.MouseEnteredAndExited | NSTrackingAreaOptions.ActiveAlways, this, null);
            AddTrackingArea(_hoverArea);
            _cursor = NSCursor.CurrentSystemCursor;

            // Initialize properties.
            Film = film;
            FilmAction = action;
        }
        #endregion

        #region Override Methods
        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Draw the subsection label.
            using(CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Paint the button's surface.
                CGPath path = new CGPath();
                CGRect frame = new CGRect(0, 0, Frame.Width, Frame.Height);
                path.AddRect(frame);
                context.SetFillColor(NSColor.FromCalibratedWhite(0.95f, 1.0f).CGColor);
                context.SetStrokeColor(Film.SubsectionColor.CGColor);
                context.AddPath(path);
                context.DrawPath(CGPathDrawingMode.Fill);

                // Draw the subsection name.
                CTStringAttributes attributes = new CTStringAttributes();
                attributes.ForegroundColor = Film.SubsectionColor.CGColor;
                attributes.BackgroundColor = NSColor.Clear.CGColor;
                context.TextPosition = new CGPoint(_horizontalTextOffset, _verticalTextOffset);
                var attributedString = new NSAttributedString(Film.SubsectionName, attributes);
                using(var textLine = new CTLine(attributedString))
                {
                    textLine.Draw(context);
                }
            }
            NeedsDisplay = true;
        }
        #endregion

        #region Override Mouse Handling Methods
        public override void MouseDown(NSEvent theEvent)
        {
            base.MouseDown(theEvent);
            _cursor.Pop();
            FilmAction(Film);
        }

        public override void MouseEntered(NSEvent theEvent)
        {
            base.MouseEntered(theEvent);
            _cursor = NSCursor.PointingHandCursor;
            _cursor.Push();
        }

        public override void MouseExited(NSEvent theEvent)
        {
            base.MouseExited(theEvent);
            _cursor.Pop();
        }
        #endregion
    }
}
