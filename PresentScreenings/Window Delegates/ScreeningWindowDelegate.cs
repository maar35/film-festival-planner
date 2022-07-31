using System;
using AppKit;

namespace PresentScreenings.TableView
{
    public class ScreeningWindowDelegate : NSWindowDelegate
    {
        #region Computed Properties
        public NSWindow Window { get; set; }
        #endregion

        #region Constructors
        public ScreeningWindowDelegate(NSWindow window)
        {
            Window = window;
        }
        #endregion

        #region Override Methods
        public override bool WindowShouldClose(Foundation.NSObject sender)
        {
            // is the window dirty?
            if (Window.DocumentEdited)
            {
                string messageText = "Save Screening Data";
                string informativeText = "Save screening data before closing window?";
                return AlertRaiser.RunDirtyWindowAlert(messageText, informativeText, this, SaveAction);
            }
            return true;
        }
        #endregion

        #region Private methods
        private void SaveAction(NSWindowDelegate windowDelegate)
        {
            var window = (windowDelegate as ScreeningWindowDelegate).Window;
            var viewController = window.ContentViewController as ScreeningDialogController;
            viewController.CloseDialog();
        }
        #endregion
    }
}
