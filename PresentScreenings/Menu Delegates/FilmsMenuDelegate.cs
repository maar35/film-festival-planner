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
        private const int _showFilmsMenuItemTag = 501;
        private const int _toggleTypeMatchMethodMenuItemTag = 502;
        private const int _showFilmInfoMenuItemTag = 503;
        private const int _combineTitlesMenuItemTag = 504;
        private const int _uncombineTitleMenuItemTag = 505;
        private readonly AppDelegate _app;
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
                if (_app.CombineTitleController != null || _app.UncombineTitleController != null || _app.FilmInfoController != null)
                {
                    item.Enabled = false;
                    continue;
                }

                // Take action based on the menu tag.
                FilmRatingDialogController controller = _app.FilmsDialogController;
                switch (item.Tag)
                {
                    case _showFilmsMenuItemTag:
                        item.Enabled = controller == null && _app.Controller.ViewIsActive();
                        break;
                    case _toggleTypeMatchMethodMenuItemTag:
                        item.Enabled = controller != null;
                        break;
                    case _showFilmInfoMenuItemTag:
                        item.Enabled = controller != null && !controller.TextBeingEdited && controller.OneFilmSelected();
                        break;
                    case _combineTitlesMenuItemTag:
                        item.Enabled = controller != null && !controller.TextBeingEdited && controller.MultipleFilmsSelected();
                        break;
                    case _uncombineTitleMenuItemTag:
                        item.Enabled = controller != null && !controller.TextBeingEdited && controller.OneFilmSelected();
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
