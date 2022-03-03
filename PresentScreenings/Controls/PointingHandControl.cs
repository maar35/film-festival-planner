using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Pointing hand control, abstract class to support the cursor changing
    /// into a pointing hand when hovering over the control frame.
    /// </summary>

    public abstract class PointingHandControl : NSControl
    {
        #region Private Members
        private NSTrackingArea _hoverArea;
        private NSCursor _cursor;
        private readonly NSTrackingAreaOptions _options = NSTrackingAreaOptions.CursorUpdate
                                                          | NSTrackingAreaOptions.ActiveAlways;
        #endregion

        #region Constructors
        public PointingHandControl(CGRect frame) : base(frame)
        {
            // Initialize mouse hovering.
            _hoverArea = new NSTrackingArea(Bounds, _options, this, null);
            AddTrackingArea(_hoverArea);
            _cursor = NSCursor.CurrentSystemCursor;
        }
        #endregion

        #region Override Methods
        // --------------------------------------------------------------------------------
        // Handle mouse with Override Methods.
        // NOTE: Use either this method or Gesture Recognizers, NOT both!
        // --------------------------------------------------------------------------------
        public override void CursorUpdate(NSEvent theEvent)
        {
            base.CursorUpdate(theEvent);
            if (Enabled)
            {
                _cursor = NSCursor.PointingHandCursor;
                _cursor.Set();
            }
        }
        #endregion
    }
}
