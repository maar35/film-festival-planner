using System;
using System.Collections.Generic;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// My attendance titler, sete the title of objects that implement the
    /// ITitled interface, based on an attendance status.
    /// </summary>

    static public class MyAttendanceTitler
    {
        #region Private Members
        static Dictionary<bool, string> _attendanceControlText;
        #endregion

        #region Constructors
        static MyAttendanceTitler()
        {
            _attendanceControlText = new Dictionary<bool, string> { };
            _attendanceControlText[true] = "Unattend";
            _attendanceControlText[false] = "Attend";
        }
        #endregion

        #region Public Methods
        static public void SetTitle(ITitled control, bool attendance)
        {
            control.SetTitle(_attendanceControlText[attendance]);
        }

        static public void SetTitle(ITitled control, Screening screening)
        {
            SetTitle(control, screening.IAttend);
        }
        #endregion
    }
}
