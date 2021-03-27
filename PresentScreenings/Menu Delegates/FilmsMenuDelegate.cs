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
        private const int _visitFilmWebsiteMenuItemTag = 504;
        private const int _combineTitlesMenuItemTag = 505;
        private const int _uncombineTitleMenuItemTag = 506;
        private readonly AppDelegate _app;
        private NSMenu _filmsMenu;
        #endregion

        #region Constructors
        public FilmsMenuDelegate(AppDelegate app, NSMenu filmsMenu)
        {
            _app = app;
            _filmsMenu = filmsMenu;
            PopulateVisitWebsiteMenuItem();
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
                // If one of the film dialogs is active, all menu items must be
                // inactive, except items Visit Film Website and Show Film Info
                // when the Film Info dialog or the Screening Info dialog runs.
                if (_app.CombineTitleController == null
                    && _app.UncombineTitleController == null
                    && (item.Tag == _visitFilmWebsiteMenuItemTag || _app.FilmInfoController == null)
                    && (item.Tag == _visitFilmWebsiteMenuItemTag || _app.Controller.ScreeningInfoDialog == null)
                    || (item.Tag == _visitFilmWebsiteMenuItemTag && _app.AnalyserDialogController != null)
                    || (item.Tag == _showFilmInfoMenuItemTag && _app.Controller.ScreeningInfoDialog != null)
                    || (item.Tag == _showFilmInfoMenuItemTag && _app.Controller.RunningPopupsCount == 0)
                    )
                {
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
                            item.Enabled = _app.Controller.ScreeningInfoDialog != null
                                || _app.Controller.RunningPopupsCount == 0
                                || (controller != null
                                    && !controller.TextBeingEdited
                                    && controller.OneFilmSelected());
                            break;
                        case _visitFilmWebsiteMenuItemTag:
                            item.Enabled = _app.FilmInfoController != null
                                || _app.Controller.ScreeningInfoDialog != null
                                || _app.Controller.RunningPopupsCount == 0
                                || (_app.AnalyserDialogController != null
                                    && _app.AnalyserDialogController.GetSelectedFilm() != null)
                                || (controller != null
                                    && !controller.TextBeingEdited
                                    && controller.OneFilmSelected());
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
                else
                {
                    item.Enabled = false;
                    continue;
                }
            }
        }
        #endregion

        #region Private Methods
        private void PopulateVisitWebsiteMenuItem()
        {
            NSMenuItem item = _filmsMenu.ItemWithTag(_visitFilmWebsiteMenuItemTag);
            item.Action = new ObjCRuntime.Selector("VisitFilmWebsite:");
        }
        #endregion
    }
}
