using System;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Go to screening dialog, created to allow the film info dialog to be
    /// segued from different view controllers.
    /// </summary>

    public abstract class GoToScreeningDialog : NSViewController
    {
        public GoToScreeningDialog(IntPtr handle) : base(handle)
        {
        }

        public abstract void GoToScreening(Screening screening);
    }
}
