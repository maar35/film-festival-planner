using AppKit;

namespace PresentScreenings.TableView
{
    public class AvailabilityWindowDelegate : NSWindowDelegate
    {
        #region Computed Properties
        public NSWindow Window { get; set; }
        #endregion

        #region Constructors
        public AvailabilityWindowDelegate(NSWindow window)
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

                string messageText = "Save Availabilities";
                string informativeText = "Save fan availabilities before closing window?";
                return AlertRaiser.RunDirtyWindowAlert(messageText, informativeText, this, SaveAction);
            }
            return true;
        }
        #endregion

        #region Private methods
        private void SaveAction(NSWindowDelegate windowDelegate)
        {
            var window = (windowDelegate as AvailabilityWindowDelegate).Window;
            var viewController = window.ContentViewController as AvailabilityDialogControler;
            viewController.CloseDialog();
        }
        #endregion
    }
}
