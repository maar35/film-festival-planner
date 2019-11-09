using System;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening label, a lable which is associated with a screening and
    /// displays need-to-know information of that screening.
    ///
    /// Ongoing attempt to make a label clickable as to raise a custum event.
    /// </summary>

    [Register("ScreeningLabel")]
    public class ScreeningLabel : NSTextField
    {
        #region Private Variables
        Screening _screening = null;
        #endregion

        #region Constructors
        public ScreeningLabel(CGRect frame, Screening screening, bool withDay = false) : base(frame)
        {
            _screening = screening;
            Font = NSFont.BoldSystemFontOfSize(ScreeningControl.FontSize);
            Editable = false;
            Bordered = false;
            StringValue = _screening.ToScreeningLabelString(withDay);
            LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            ColorView.SetScreeningColor(_screening, this);
            NeedsDisplay = true;
        }
		#endregion

        #region Override Methods
        public override void MouseDown(NSEvent theEvent)
        {
            RaiseScreeningInfoAsked();
        }
        #endregion

        #region Private Methods
        void Initialize()
        {
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;
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
