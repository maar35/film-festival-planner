﻿using System;
using System.Collections.Generic;
using System.Linq;
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
        private const int _toggleOnlyFilmsWithScreeningsMenuItemTag = 502;
        private const int _toggleTypeMatchMethodMenuItemTag = 503;
        private const int _showFilmInfoMenuItemTag = 504;
        private const int _visitFilmWebsiteMenuItemTag = 505;
        private const int _combineTitlesMenuItemTag = 506;
        private const int _uncombineTitleMenuItemTag = 507;
        private const int _reloadRatingsMenuItemTag = 508;
        private const int _firstExtraMenuItemTag = 520;
        private int _currentTag;
        private int _extraFilmNumber;
        private readonly AppDelegate _app;
        private Dictionary<nint, bool> _enabledByTag;
        #endregion

        #region Properties
        public static int ToggleOnlyFilmsWithScreeningsMenuItemTag => _toggleOnlyFilmsWithScreeningsMenuItemTag;
        public static int ToggleTypeMatchMethodMenuItemTag => _toggleTypeMatchMethodMenuItemTag;
        public static int ReloadRatingsMenuItemTag => _reloadRatingsMenuItemTag;
        private ViewController ViewController => _app.Controller;
        private FilmRatingDialogController RatingController => _app.FilmsDialogController;
        private ScreeningDialogController ScreeningInfoController => ViewController.ScreeningInfoDialog;
        private FilmInfoDialogController FilmInfoController => _app.FilmInfoController;
        private AnalyserDialogController AnalyserController => _app.AnalyserDialogController;
        private CombineTitlesSheetController CombineTitlesController => _app.CombineTitleController;
        private UncombineTitlesSheetController UncombineTitlesController => _app.UncombineTitleController;
        #endregion

        #region Constructors
        public FilmsMenuDelegate(AppDelegate app)
        {
            // Initialize private members.
            _app = app;
            _enabledByTag = new Dictionary<nint, bool> { };
        }
        #endregion

        #region Override Methods
        public override void MenuWillHighlightItem(NSMenu menu, NSMenuItem item)
        {
        }

        public override void NeedsUpdate(NSMenu menu)
        {
            // Create extra menu items for screened films and combinations.
            PopulateExtraMenuItems(menu);

            // Process every item in the menu.
            foreach (NSMenuItem item in menu.Items)
            {
                // If the Combine or Uncombine film dialog is active, all menu
                // items must be inactive.
                if (CombineTitlesController != null || UncombineTitlesController != null)
                {
                    item.Enabled = false;
                    continue;
                }

                // Take action based on the extra menu item tags dictionary.
                if (_enabledByTag.Keys.Contains(item.Tag))
                {
                    item.Enabled = _enabledByTag[item.Tag];
                    continue;
                }

                // Take action based on the menu item tag.
                switch (item.Tag)
                {
                    case _showFilmsMenuItemTag:
                        item.Enabled = RatingController == null && ViewController.ViewIsActive();
                        break;
                    case _toggleOnlyFilmsWithScreeningsMenuItemTag:
                    case _toggleTypeMatchMethodMenuItemTag:
                        item.Enabled = RatingController != null
                                        && FilmInfoController == null;
                        break;
                    case _reloadRatingsMenuItemTag:
                        item.Enabled = RatingController != null
                                        || ScreeningInfoController != null
                                        || ViewController.RunningPopupsCount == 0;
                        break;
                    case _showFilmInfoMenuItemTag:
                        item.Enabled = ScreeningInfoController != null
                                        || ViewController.RunningPopupsCount == 0
                                        || (RatingController != null
                                            && RatingController.OneFilmSelected()
                                            && FilmInfoController == null);
                        break;
                    case _visitFilmWebsiteMenuItemTag:
                        item.Enabled = ScreeningInfoController != null
                                        || ViewController.RunningPopupsCount == 0
                                        || (RatingController != null
                                            && RatingController.OneFilmSelected())
                                        || FilmInfoController != null
                                        || (AnalyserController != null
                                            && AnalyserController.GetSelectedFilm() != null);
                        break;
                    case _combineTitlesMenuItemTag:
                        item.Enabled = RatingController != null
                                        && RatingController.MultipleFilmsSelected()
                                        && FilmInfoController == null;
                        ;
                        break;
                    case _uncombineTitleMenuItemTag:
                        item.Enabled = RatingController != null
                                        && RatingController.OneFilmSelected()
                                        && FilmInfoController == null;
                        ;
                        break;
                    default:
                        item.Enabled = false;
                        break;
                }
            }
        }
        #endregion

        #region Private Methods
        private void PopulateExtraMenuItems(NSMenu menu)
        {
            // Remove current extra menu items.
            foreach (nint tag in _enabledByTag.Keys)
            {
                menu.RemoveItem(menu.ItemWithTag(tag));
            }
            _enabledByTag = new Dictionary<nint, bool> { };


            // Get the current film.
            Film film = null;
            if (RatingController != null)
            {
                film = RatingController.CurrentFilm;
            }
            else
            {
                film = ViewController.CurrentFilm;
            }

            // Create extra menu items if applicable.
            if (film != null)
            {
                FilmInfo filmInfo = ViewController.GetFilmInfo(film.FilmId);
                if (filmInfo != null)
                {
                    CreateAllExtraMenuItems(menu, filmInfo);
                }
            }
        }

        private void CreateAllExtraMenuItems(NSMenu menu, FilmInfo filmInfo)
        {
            // Initialize private member variables.
            _currentTag = _firstExtraMenuItemTag;
            _extraFilmNumber = 0;

            // Create the screened films items.
            if (filmInfo.ScreenedFilms.Count > 0)
            {
                var screenedFilms = filmInfo.ScreenedFilms
                    .Select(sf => ViewController.GetFilmById(sf.ScreenedFilmId))
                    .ToList();
                CreateExtraMenuItems(menu, screenedFilms, "Screened Films");
            }

            // Create the combination program items.
            if (filmInfo.CombinationProgramIds.Count > 0)
            {
                var combinationFilms = filmInfo.CombinationProgramIds
                    .Select(id => ViewController.GetFilmById(id))
                    .ToList();
                CreateExtraMenuItems(menu, combinationFilms, "Combination Program(s)");
            }

            // Add an inactive stub menu item if no extra films are available.
            if (filmInfo.ScreenedFilms.Count == 0 && filmInfo.CombinationProgramIds.Count == 0)
            {
                var emptyList = new List<Film> { };
                CreateExtraMenuItems(menu, emptyList, "No combinations involved");
            }
        }

        private void CreateExtraMenuItems(NSMenu menu, List<Film> extraFilms, string headerTitle)
        {
            // Create the separator item.
            _currentTag += 1;
            NSMenuItem seperatorItem = NSMenuItem.SeparatorItem;
            seperatorItem.Tag = _currentTag;
            _enabledByTag.Add(_currentTag, false);
            menu.AddItem(seperatorItem);

            // Create the header item.
            _currentTag += 1;
            NSMenuItem headerItem = new NSMenuItem
            {
                Title = headerTitle,
                Tag = _currentTag,
                IndentationLevel = 1,
            };
            _enabledByTag.Add(_currentTag, false);
            menu.AddItem(headerItem);

            // Create an item for each extra film.
            NSEventModifierMask mask = NSEventModifierMask.ControlKeyMask | NSEventModifierMask.CommandKeyMask;
            foreach (var extraFilm in extraFilms)
            {
                _currentTag += 1;
                _extraFilmNumber += 1;
                NSMenuItem item = new NSMenuItem
                {
                    Title = extraFilm.ToString(),
                    Tag = _currentTag,
                    Action = new ObjCRuntime.Selector("NavigateToFilm:"),
                    Identifier = extraFilm.FilmId.ToString(),
                    KeyEquivalent = _extraFilmNumber.ToString(),
                    KeyEquivalentModifierMask = mask,
                };
                var enabled = RatingController != null
                    && RatingController.OneFilmSelected()
                    && CombineTitlesController == null
                    && UncombineTitlesController == null;
                _enabledByTag.Add(_currentTag, enabled);
                menu.AddItem(item);
            }
        }
        #endregion
    }
}
