using AppKit;

namespace PresentScreenings.TableView
{
    public class FilmRatingWindowDelegate : NSWindowDelegate
    {
        #region Computed Properties
        public NSWindow Window { get; set; }
        #endregion

        #region Constructors
        public FilmRatingWindowDelegate(NSWindow window)
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

                string messageText = "Save Film Ratings";
                string informativeText = "Save film ratings before closing window?";
                return AlertRaiser.RunDirtyWindowAlert(messageText, informativeText, this, SaveAction);
            }
            return true;
        }
        #endregion

        #region Private methods
        private void SaveAction(NSWindowDelegate windowDelegate)
        {
            var window = (windowDelegate as FilmRatingWindowDelegate).Window;
            var viewController = window.ContentViewController as FilmRatingDialogController;
            viewController.CloseDialog();
        }
        #endregion
    }
}
