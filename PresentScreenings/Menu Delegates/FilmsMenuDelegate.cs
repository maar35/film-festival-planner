using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Films menu delegate, enables and disables the items of the films menu,
    /// based on their tag value and methods of the given View Controller.
    /// </summary>

    public class FilmsMenuDelegate : NSMenuDelegate
    {
        #region Private Members
        const int _showFilmsMenuItemTag = 501;
        const int _toggleTypeMatchMethodMenuItemTag = 502;
        const int _showFilmInfoMenuItemTag = 503;
        const int _combineTitlesMenuItemTag = 504;
        const int _uncombineTitleMenuItemTag = 505;
        const int _downloadFilmInfoMenuItemTag = 506;
        AppDelegate _app;
        #endregion

        #region Constructors
        public FilmsMenuDelegate(AppDelegate app)
        {
            _app = app;
        }
        #endregion

        #region Override Methods
        public override void MenuWillHighlightItem(NSMenu menu, NSMenuItem item)
        {
        }

        public override void NeedsUpdate(NSMenu menu)
        {
            // Process every item in the menu
            foreach (NSMenuItem item in menu.Items)
            {
                // If one of the film dialogs is active, all menu items must be inactive.
                if (_app.CombineTitleController != null || _app.UncombineTitleController != null || _app.filmInfoController != null)
                {
                    item.Enabled = false;
                    continue;
                }

                // Take action based on the menu tag.
                switch (item.Tag)
                {
                    case _showFilmsMenuItemTag:
                        item.Enabled = _app.FilmsDialogController == null && _app.Controller.ViewIsActive();
                        break;
                    case _toggleTypeMatchMethodMenuItemTag:
                        item.Enabled = _app.FilmsDialogController != null;
                        break;
                    case _showFilmInfoMenuItemTag:
                        item.Enabled = _app.FilmsDialogController != null && _app.FilmsDialogController.OneFilmSelected();
                        break;
                    case _combineTitlesMenuItemTag:
                        item.Enabled = _app.FilmsDialogController != null && _app.FilmsDialogController.MultipleFilmsSelected();
                        break;
                    case _uncombineTitleMenuItemTag:
                        item.Enabled = _app.FilmsDialogController != null && _app.FilmsDialogController.OneFilmSelected();
                        break;
                    case _downloadFilmInfoMenuItemTag:
                        item.Enabled = true;
                        break;
                    default:
                        item.Enabled = false;
                        break;
                }
            }
        }
        #endregion
    }
}
