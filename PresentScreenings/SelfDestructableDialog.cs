using System;
using AppKit;

namespace PresentScreenings.TableView
{
    public abstract class SelfDestructableDialog : NSViewController
    {
        public SelfDestructableDialog(IntPtr handle) : base(handle)
        {
        }

        public abstract void GoToScreening(Screening screening);
    }
}
