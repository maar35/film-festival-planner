using System;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening button, button which is associated with a screening and
    /// displays need-to-know information of that screening.
    /// </summary>

    public class ScreeningButton : NSButton
    {
        #region Private Members
        Screening _screening;
        #endregion

        #region Constructors
        public ScreeningButton(CGRect frame, Screening screening) : base(frame)
        {
            Initialize();
            _screening = screening;
            Font = NSFont.BoldSystemFontOfSize(13);
            Bordered = false;
            StringValue = string.Empty;
            base.UsesSingleLineMode = false;
            LineBreakMode = NSLineBreakMode.TruncatingMiddle;
			NeedsDisplay = true;
        }
        #endregion

        #region Override Methods
        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Use Core Graphic routines to draw our UI
            using (CGContext g = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                CGPath path = new CGPath();
                CGRect frame = new CGRect(0, 0, base.Frame.Width, base.Frame.Height);
                path.AddRect(frame);
                ColorView.SetScreeningColor(_screening, g);
                g.AddPath(path);
                g.DrawPath(CGPathDrawingMode.Fill);

                float fontSize = 1.0f;
                g.TranslateCTM(0, fontSize);
                g.SetLineWidth((nfloat)0.5);
                g.SetTextDrawingMode(CGTextDrawingMode.Fill);
                ColorView.SetScreeningColor(_screening, g, true);
                g.SelectFont("Helvetica-Bold", fontSize, CGTextEncoding.MacRoman);
				g.TextPosition = new CGPoint(2, 2 + 12);
                string labelString = _screening.ToScreeningLabelString();
                string[] lines = labelString.Split('\n');
                g.ShowText(lines[0]);
                g.TextPosition = new CGPoint(2, 2 + 25);
                g.ShowText(lines[1]);
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
