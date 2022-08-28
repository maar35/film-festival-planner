using System;
using AppKit;
using PresentScreenings.TableView.Utilities;

namespace PresentScreenings.TableView
{
    public class ScreeningRelatedWindowDelegate : BaseWindowDelegate
    {
        #region Constructors
        public ScreeningRelatedWindowDelegate(NSWindow window, Action saveAction) : base(window, saveAction)
        {
            Subject = "screening info";
        }
        #endregion

        #region Override Methods
        public override bool WindowShouldClose(Foundation.NSObject sender)
        {
            // Is the window dirty?
            if (Window.DocumentEdited)
            {
                // Don't save the screening info data if it is already saved in
                // an earlier closed window while terminating the application.
                if (!ScreeningInfo.ScreeningInfoChanged)
                {
                    Window.DocumentEdited = false;
                }
            }

            // Let the base delegate decide about closing the window.
            return base.WindowShouldClose(sender);
        }
        #endregion
    }
}
