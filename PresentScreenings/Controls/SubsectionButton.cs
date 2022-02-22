using System;
using AppKit;
using CoreGraphics;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Subsection button, button to represent the subsection of a film in the
    /// film rating dialog.
    /// It supports filtering of the subsection of the associated film.
    /// </summary>

    public class SubsectionButton : NSButton
    {
        #region Private constants
        private const float _horizontalTextOffset = 2;
        private const float _verticalTextOffset = 4;
        #endregion

        #region Properties
        Film Film { get; }
        #endregion

        #region Constructors
        public SubsectionButton(CGRect frame, Film film) : base(frame)
        {
            Initialize();
            Film = film;
        }
        #endregion

        #region Override Methods
        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Draw the subsection label.
            using(CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Equalize the button's surface.
                CGPath path = new CGPath();
                CGRect frame = new CGRect(0, 0, Frame.Width, Frame.Height);
                path.AddRect(frame);
                context.SetFillColor(NSColor.FromCalibratedWhite(0.95f, 1.0f).CGColor);
                context.SetStrokeColor(Film.SubsectionColor.CGColor);
                context.AddPath(path);
                context.DrawPath(CGPathDrawingMode.Fill);

                // Draw the subsection name.
                context.ScaleCTM(1, -1);
                context.TranslateCTM(0, -Frame.Height);
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

        #region Private Methods
        void Initialize()
        {
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;
        }
        #endregion
    }
}
