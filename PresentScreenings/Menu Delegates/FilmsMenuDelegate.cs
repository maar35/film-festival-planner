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
        private const int _toggleHideScreeninglessMenuItemTag = 502;
        private const int _toggleTypeMatchMethodMenuItemTag = 503;
        private const int _showFilmInfoMenuItemTag = 504;
        private const int _visitFilmWebsiteMenuItemTag = 505;
        private const int _combineTitlesMenuItemTag = 506;
        private const int _uncombineTitleMenuItemTag = 507;
        private readonly AppDelegate _app;
        private NSMenu _filmsMenu;
        #endregion

        #region Properties
        public static int ToggleHideScreeninglessMenuItemTag => _toggleHideScreeninglessMenuItemTag;
        public static int ToggleTypeMatchMethodMenuItemTag => _toggleTypeMatchMethodMenuItemTag;
        #endregion

        #region Constructors
        public FilmsMenuDelegate(AppDelegate app, NSMenu filmsMenu)
        {
            // Initialize private members.
            _app = app;
            _filmsMenu = filmsMenu;
        }
        #endregion

        #region Override Methods
        public override void MenuWillHighlightItem(NSMenu menu, NSMenuItem item)
        {
        }

        public override void NeedsUpdate(NSMenu menu)
        {
            // Define some aliases for improved readability.
            ViewController viewController = _app.Controller;
            FilmRatingDialogController ratingController = _app.FilmsDialogController;
            ScreeningDialogController screeningInfoController = viewController.ScreeningInfoDialog;
            FilmInfoDialogController filmInfoController = _app.FilmInfoController;
            AnalyserDialogController analyserController = _app.AnalyserDialogController;

            // Process every item in the menu
            foreach (NSMenuItem item in menu.Items)
            {
                // If the Combine or Uncombine film dialog is active, all menu
                // items must be inactive.
                if (_app.CombineTitleController != null || _app.UncombineTitleController != null)
                {
                    item.Enabled = false;
                    continue;
                }

                // Take action based on the menu tag.
                switch (item.Tag)
                {
                    case _showFilmsMenuItemTag:
                        item.Enabled = ratingController == null && viewController.ViewIsActive();
                        break;
                    case _toggleHideScreeninglessMenuItemTag:
                        item.Enabled = ratingController != null;
                        break;
                    case _toggleTypeMatchMethodMenuItemTag:
                        item.Enabled = ratingController != null;
                        break;
                    case _showFilmInfoMenuItemTag:
                        item.Enabled = screeningInfoController != null
                                        || viewController.RunningPopupsCount == 0
                                        || (ratingController != null
                                            && !ratingController.TextBeingEdited
                                            && ratingController.OneFilmSelected()
                                            && filmInfoController == null);
                        break;
                    case _visitFilmWebsiteMenuItemTag:
                        item.Enabled = screeningInfoController != null
                                        || viewController.RunningPopupsCount == 0
                                        || (ratingController != null
                                            && !ratingController.TextBeingEdited
                                            && ratingController.OneFilmSelected())
                                        || filmInfoController != null
                                        || (analyserController != null
                                            && analyserController.GetSelectedFilm() != null);
                        break;
                    case _combineTitlesMenuItemTag:
                        item.Enabled = ratingController != null
                                        && !ratingController.TextBeingEdited
                                        && ratingController.MultipleFilmsSelected();
                        break;
                    case _uncombineTitleMenuItemTag:
                        item.Enabled = ratingController != null
                                        && !ratingController.TextBeingEdited
                                        && ratingController.OneFilmSelected();
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
