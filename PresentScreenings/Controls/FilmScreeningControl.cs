using System;
using Foundation;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film screening control, a button in the Info Screening View to open the
    /// Info Screening View of another screening of the same film.
    /// </summary>

    [Register("FilmScreeningControl")]
    public class FilmScreeningControl : NSControl
    {
        #region Constants
        private const float _yVisualCorrection = 1;
        #endregion

        #region Private Variables
        bool _selected = false;
        Screening _screening = null;
        #endregion

        #region Properties
        public bool Selected
        {
            get => _selected;
            set
            {
                _selected = value;
                NeedsDisplay = true;
            }
        }
        #endregion

        #region Constructors
        public FilmScreeningControl(CGRect controlRect, Screening screening) : base(controlRect)
        {
            // Initialize control features
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;
			
			// Initialize custom features
            _screening = screening;
        }
        #endregion

        #region Override Methods
        public override void MouseDown(NSEvent theEvent)
        {
            base.MouseDown(theEvent);
            RaiseScreeningInfoAsked();
        }

        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Use Core Graphic routines to draw our UI
			using (CGContext g = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Color the control surface
                FillControlRect(g);

                // Draw a frame if something's wrong with the tickets
                if (ScreeningInfo.TicketStatusNeedsAttention(_screening))
                {
					ColorView.DrawTicketAvalabilityFrame(g, _screening, Frame);
                }

                // Draw Sold Out Symbol
                if (_screening.SoldOut)
                {
                    ColorView.DrawSoldOutSymbol(g, Selected, Frame);
                }

                // Draw the Autometically Planned symbol.
                if (_screening.AutomaticallyPlanned)
                {
                    ScreeningControl.InitializeCoreText(g, Selected);
                    ScreeningControl.DrawText(
                        g,
                        ScreeningControl.AutomaticallyPlannedSymbol,
                        Frame.Width / 3,
                        _yVisualCorrection + (Frame.Height - ScreeningControl.FontSize) / 2);
                }
            }
        }
        #endregion

        #region Private Methods
        void FillControlRect(CGContext g)
        {
            var path = new CGPath();
            nfloat w = Frame.Width;
            nfloat h = Frame.Height;
            path.AddRect(new CGRect(0, 0, w, h));
            ColorView.ClickPadBackgroundColor(Selected).SetFill();
            path.CloseSubpath();
            g.AddPath(path);
            g.DrawPath(CGPathDrawingMode.Fill);
        }
        #endregion

        #region Public Methods
        public void ReDraw()
        {
            NeedsDisplay = true;
        }
        #endregion

        #region Events
        public EventHandler ScreeningInfoAsked;

        internal void RaiseScreeningInfoAsked()
        {
            ScreeningInfoAsked?.Invoke(this, EventArgs.Empty);
        }
        #endregion
	}
}
