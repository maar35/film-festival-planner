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
        public AttendanceCheckbox(IntPtr handle) : base(handle)
        {
        }

        public AttendanceCheckbox(CGRect frame) : base(frame)
        {
            SetButtonType(NSButtonType.Switch);
        }
        #endregion

        #region Override Methods
        public override void AwakeFromNib()
        {
            base.AwakeFromNib();
        }
        #endregion

        #region Public Methods
        static public NSCellStateValue SetAttendanceState(bool isattending)
        {
            return isattending? NSCellStateValue.On : NSCellStateValue.Off;
        }
        #endregion

        #region Events
        public EventHandler FriendAttendanceChanged;

        internal void RaiseFriendAttendanceChanged()
        {
            FriendAttendanceChanged?.Invoke(this, EventArgs.Empty);
        }

        #endregion
    }
}