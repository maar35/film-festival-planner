using System;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening control, when clicked opens a dialog to view and edit editable
    /// screening data.
    /// The control displays a summary of its screening. The display area is
    /// only clickable in Use Core Graphics mode.
    /// </summary>

    public class DaySchemaScreeningControl : PointingHandControl
    {
        #region Private Variables
        private static nfloat _xExtension;
        private bool _selected = false;
        #endregion

        #region Application Access
        private static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public static bool UseCoreGraphics { get; set; }
        public Screening Screening { get; }
        public CGRect ClickpadRect { get; }
        public CGRect LabelRect { get; }
        public bool Selected { get => _selected; set => SetSelected(value); }
        #endregion

        #region Constructors
        public DaySchemaScreeningControl(CGRect screeningRect, Screening screening) : base(GetExtendedRect(screeningRect))
        {
            // Initialize control features.
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;

            // Initialize properties.
            Screening = screening;
            ClickpadRect = new CGRect(0, 0, _xExtension - 2, Frame.Height);
            LabelRect = new CGRect(_xExtension, 0, Frame.Width - _xExtension, Frame.Height);

            // Add a control depending whether core graphics are used to draw
            // the label. If core graphics are used, the label is clickable.
            if (UseCoreGraphics)
            {
                var control = new ClickableScreeningLabel(LabelRect, Screening);
                control.Activated += (sender, e) => ShowScreeningInfo(Screening);
				base.AddSubview(control);
            }
            else
            {
                var label = new ScreeningLabel(LabelRect, Screening);
				base.AddSubview(label);
            }
        }
        #endregion

        #region Override Methods
        public override void MouseDown(NSEvent theEvent)
        {
            base.MouseDown(theEvent);
            RaiseScreeningSelected();
        }

        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Use Core Graphics routines to draw our UI.
            using (CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                ColorView.DrawStandardClickpad(context, Screening, ClickpadRect, Selected);
            }
        }
        #endregion

        #region Private Methods
        private void SetSelected(bool selected)
        {
            _selected = selected;
            if (selected)
            {
                // Scroll the view as to make the control visible.
                var plan = _app.Controller.Plan;
                var table = _app.Controller.TableView;
                _app.Controller.TableView.ScrollRowToVisible(plan.CurrDayScreens.IndexOf(plan.CurrScreen));
                var x = Frame.X;
                var y = Frame.Y + plan.CurrDayScreens.IndexOf(plan.CurrScreen) * (table.RowHeight + table.IntercellSpacing.Height);
                var frame = new CGRect(x, y, Frame.Width, Frame.Height);
                _app.Controller.TableView.ScrollRectToVisible(frame);
            }

            // Force a redraw.
            NeedsDisplay = true;
        }

        private static CGRect GetExtendedRect(CGRect screeningRect)
        {
            _xExtension = screeningRect.Height;
            nfloat x = screeningRect.X;
            nfloat y = screeningRect.Y;
            nfloat w = screeningRect.Width;
            nfloat h = screeningRect.Height;
            return new CGRect(x - _xExtension, y, w + _xExtension, h);
        }

        private void ShowScreeningInfo(Screening screening)
        {
            _app.Controller.GoToScreening(screening);
        }
        #endregion

        #region Events
        public event EventHandler ScreeningSelected;

        internal void RaiseScreeningSelected()
        {
            ScreeningSelected?.Invoke(this, EventArgs.Empty);
        }
        #endregion
    }
}
