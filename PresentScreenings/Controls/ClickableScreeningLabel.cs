using System;
using AppKit;
using CoreGraphics;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening button, button which is associated with a screening and
    /// displays need-to-know information of that screening.
    /// </summary>

    public class ClickableScreeningLabel : PointingHandControl
    {
        #region Private Constants
        private const float _lineHeight = ControlsFactory.StandardLineHeight;
        #endregion

        #region Private Members
        bool _withDay;
        Screening _screening;
        Action<Screening> _goToScreening;
        #endregion

        #region Properties
        public Screening Screening => _screening;
        #endregion

        #region Constructors
        public ClickableScreeningLabel(
            CGRect frame,
            Screening screening,
            bool withDay = false,
            Action<Screening> goToScreening = null) : base(frame)
        {
            Initialize();
            _screening = screening;
            _withDay = withDay;
            _goToScreening = goToScreening;
			NeedsDisplay = true;
        }
        #endregion

        #region Override Methods
        public override void MouseDown(NSEvent theEvent)
        {
            base.MouseDown(theEvent);
            _goToScreening?.Invoke(Screening);
        }

        public override void DrawRect(CGRect dirtyRect)
        {
                base.DrawRect(dirtyRect);

            // Use Core Graphic routines to draw the UI.
            using (CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Fill the screening color.
                CGPath path = new CGPath();
                CGRect frame = new CGRect(0, 0, base.Frame.Width, base.Frame.Height);
                path.AddRect(frame);
                ColorView.SetScreeningColor(_screening, context);
                context.AddPath(path);
                context.DrawPath(CGPathDrawingMode.Fill);

                // Draw screening information.
                context.TranslateCTM(2, ControlsFactory.VerticalTextOffset);
                context.SetTextDrawingMode(CGTextDrawingMode.Fill);
                ColorView.SetScreeningColor(_screening, context, true);
                CTStringAttributes attrs = new CTStringAttributes();
                attrs.ForegroundColorFromContext = true;
                attrs.Font = ControlsFactory.StandardCtBoldFont;
                var textPosition = new CGPoint(0, _lineHeight);
                string[] lines = _screening.ToScreeningLabelString(_withDay).Split(Environment.NewLine);
                foreach (var line in lines)
                {
                    context.TextPosition = textPosition;
                    var attributedString = new NSAttributedString(line, attrs);
                    using (var textLine = new CTLine(attributedString))
                    {
                        textLine.Draw(context);
                    }
                    textPosition.Y -= _lineHeight;
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
