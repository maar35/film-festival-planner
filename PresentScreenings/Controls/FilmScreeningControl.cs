using System;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Film screening control, a button in the Info Screening View to open the
    /// Info Screening View of another screening of the same film.
    /// </summary>

    public class FilmScreeningControl : PointingHandControl
    {
        #region Constants
        private const float _yVisualCorrection = 1;
        #endregion

        #region Private Variables
        private bool _selected = false;
        private Screening _screening = null;
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
            // Initialize control features.
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;

            // Initialize custom features.
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
            using (CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                CGRect clickpadFrame = new CGRect(0, 0, Frame.Width, Frame.Height);
                ColorView.DrawStandardClickpad(context, _screening, clickpadFrame, Selected);
            }
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
