using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    public class FilmInfoControl : NSControl
    {
        #region Private Constants
        private const float _lineHeight = ControlsFactory.StandardLineHeight;
        #endregion

        #region Properties
        public FilmInfo FilmInfo;
        #endregion

        #region Constructors
        public FilmInfoControl(CGRect frame, FilmInfo filmInfo) : base(frame)
        {
            FilmInfo = filmInfo;
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;
        }
        #endregion

        #region Override Methods
        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Use core graphics to draw the information.
            using (CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Draw attributed film information.
                context.SetTextDrawingMode(CGTextDrawingMode.Fill);
                var attrText = FilmInfo.ToAttributedString();
                attrText.DrawInRect(Frame);
            }
            NeedsDisplay = true;
        }
        #endregion
    }
}
