using System;
using AppKit;
using Foundation;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Attendance Checkbox.
    /// </summary>

    [Register("AttendanceCheckbox")]
    public class AttendanceCheckbox : NSButton
    {
		#region Constructors
        public AttendanceCheckbox(CGRect frame) : base(frame)
        {
            SetButtonType(NSButtonType.Switch);
        }
        #endregion

        #region Public Methods
        static public NSCellStateValue GetAttendanceState(bool isattending)
        {
            return isattending? NSCellStateValue.On : NSCellStateValue.Off;
        }
        #endregion
    }
}
