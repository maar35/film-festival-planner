using System;
using System.Collections.Generic;
using AppKit;
using ObjCRuntime;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening menu delegate, enables/disables menu items of the Screening
    /// menu and manages their state and title.
    /// </summary>

    public class ScreeningMenuDelegate : NSMenuDelegate
    {
        #region Constants
        const int _showScreeningInfoMenuItemTag = 201;
        const int _soldOutMenuItemTag = 202;
        const int _ticketsBoughtMenuItemTag = 204;
        const int _myAttendanceMenuItemTag = 210;
        const int _filmMenuHeaderItemTag = 400;
        #endregion

        #region Private Members
        NSMenu _screeningMenu;
        AppDelegate _app;
        ViewController _controller;
        IScreeningProvider _screeningProvider;
        Film _film;
        Dictionary<nint, string> _filmFanByTag;
        static Dictionary<nint, bool> _FilmScreeningEnabledByTag;
        static Dictionary<string, Screening> _filmScreeningByMenuItemTitle;
        #endregion

        #region Properties
        public Screening Screening { get; private set; }
        public static FilmRatingDialogController FilmRatingController => ViewController.App.FilmsDialogController;
        #endregion

        #region Constructors
        public ScreeningMenuDelegate(AppDelegate app, NSMenu screeningMenu)
        {
            _app = app;
            _controller = app.Controller;
            _screeningMenu = screeningMenu;
            _FilmScreeningEnabledByTag = new Dictionary<nint, bool> { };
            _filmFanByTag = new Dictionary<nint, string> { };
            _filmScreeningByMenuItemTitle = new Dictionary<string, Screening> { };
            PopulateAttendanceMenuItems();
            InitializeFilmMenuItems();
        }
        #endregion


        #region Override Methods
        public override void MenuWillHighlightItem(NSMenu menu, NSMenuItem item)
        {
        }

        public override void NeedsUpdate(NSMenu menu)
        {
            // Get the screening provider.
            _screeningProvider = FilmRatingViewRunning() ? (IScreeningProvider)FilmRatingController : _controller;

            //Get the current film.
            var currFilm = _screeningProvider.CurrentFilm;
            if (currFilm != _film)
            {
                _film = currFilm;
                PopulateFilmScreeningsMenuItems(menu);
            }

            // Get the current screening.
            var currScreening = _screeningProvider.CurrentScreening;
            if (currScreening != Screening)
            {
                Screening = currScreening;
                PopulateFilmScreeningsMenuItems(menu);
            }

            // Process every item in the menu
            foreach (NSMenuItem item in menu.Items)
            {
                // If the combine or uncombine film dialog is active, all menu items must be inactive.
                if (_app.CombineTitleController != null || _app.UncombineTitleController != null)
                {
                    item.Enabled = false;
                    continue;
                }

                bool itemHandled = false;
                if (!itemHandled)
                {
                    // Take action based on the menu tag and the film screenings dictionary.
                    itemHandled = FilmScreeningItemIsHandled(item);
                }
                if (!itemHandled)
                {
                    // Take action on the menu tag and the film fan by tag dictionary.
                    itemHandled = AttendanceItemIsHandled(item);
                }
                if (!itemHandled)
                {
                    // Take action based on the menu tag.
                    itemHandled = ItemIsHandledByTag(item);
                }
                if (!itemHandled)
                {
                    item.Enabled = false;
                }
            }
        }
        #endregion

        #region Private Methods
        bool FilmScreeningItemIsHandled(NSMenuItem item)
        {
            if (_FilmScreeningEnabledByTag.ContainsKey(item.Tag))
            {
                item.Enabled = _FilmScreeningEnabledByTag[item.Tag];
                return true;
            }
            return false;
        }

        bool AttendanceItemIsHandled(NSMenuItem item)
        {
            if (_filmFanByTag.ContainsKey(item.Tag))
            {
                var filmFan = _filmFanByTag[item.Tag];
                if (FilmRatingViewRunning())
                {
                    item.State = NSCellStateValue.Off;
                    item.Enabled = false;
                }
                else
                {
                    item.State = Screening.FilmFanAttends(filmFan) ? NSCellStateValue.On : NSCellStateValue.Off;
                    item.Enabled = true;
                }
                return true;
            }
            return false;
        }

        bool ItemIsHandledByTag(NSMenuItem item)
        {
            bool itemHandled = true;
            switch (item.Tag)
            {
                case _showScreeningInfoMenuItemTag:
                    item.Enabled = _controller.ViewIsActive();
                    break;
                case _soldOutMenuItemTag:
                    item.Enabled = Screening != null;
                    item.State = (Screening != null && Screening.SoldOut) ? NSCellStateValue.On : NSCellStateValue.Off;
                    break;
                case _ticketsBoughtMenuItemTag:
                    item.Enabled = Screening != null;
                    item.State = (Screening != null && Screening.TicketsBought) ? NSCellStateValue.On : NSCellStateValue.Off;
                    break;
                case _filmMenuHeaderItemTag:
                    item.Title = _film != null ? _film.Title : "No screening selected";
                    item.Enabled = false;
                    break;
                default:
                    itemHandled = false;
                    break;
            }
            return itemHandled;
        }

        void PopulateAttendanceMenuItems()
        {
            foreach (var filmFan in ScreeningInfo.FilmFans)
            {
                var filmFanNumber = ScreeningInfo.FilmFans.IndexOf(filmFan) + 1;
                var item = new NSMenuItem(filmFan)
                {
                    Action = new Selector("ToggleAttendance:"),
                    Tag = _myAttendanceMenuItemTag + filmFanNumber,
                    KeyEquivalent = filmFanNumber.ToString()
                };
                _screeningMenu.AddItem(item);
                _filmFanByTag.Add(item.Tag, filmFan);
            }
        }

        void InitializeFilmMenuItems()
        {
            _screeningMenu.AddItem(NSMenuItem.SeparatorItem);
            NSMenuItem item = new NSMenuItem
            {
                Tag = _filmMenuHeaderItemTag,
                IndentationLevel = 1
            };
            _screeningMenu.AddItem(item);
        }

        /// <summary>
        /// Populates the film menu items with all screenings of the current film.
        /// </summary>
        /// <param name="menu">Menu.</param>
        /// 
        void PopulateFilmScreeningsMenuItems(NSMenu menu)
        {
            // Remove the existing screening items from the menu.
            foreach (var item in _filmScreeningByMenuItemTitle.Keys)
            {
                menu.RemoveItem(menu.ItemWithTitle(item));
            }

            // Add the screenings with same film to the Screening menu.
            int screeningNumber = 0;
            var mask = NSEventModifierMask.AlternateKeyMask | NSEventModifierMask.CommandKeyMask;
            _filmScreeningByMenuItemTitle = new Dictionary<string, Screening> { };
            _FilmScreeningEnabledByTag = new Dictionary<nint, bool> { };
            var screenings = _screeningProvider.Screenings;
            foreach (var screening in screenings)
            {
                screeningNumber += 1;
                string itemTitle = screening.ToMenuItemString();
                NSMenuItem item = new NSMenuItem(itemTitle)
                {
                    Action = new Selector("NavigateFilmScreening:"),
                    Tag = _filmMenuHeaderItemTag + screeningNumber,
                    State = NSCellStateValue.Off
                };
                if (screeningNumber <= 9)
                {
                    item.KeyEquivalent = screeningNumber.ToString();
                    item.KeyEquivalentModifierMask = mask;
                }
                menu.AddItem(item);
                _FilmScreeningEnabledByTag.Add(item.Tag, screening != Screening);
                _filmScreeningByMenuItemTitle.Add(itemTitle, screening);
            }
        }

        bool FilmRatingViewRunning()
        {
            return FilmRatingController != null;
        }
        #endregion

        #region Public Methods
        public static Screening FilmScreening(string title)
        {
            return _filmScreeningByMenuItemTitle[title];
        }

        public void ForceRepopulateFilmMenuItems()
        {
            _film = null;
            Screening = null;
        }
        #endregion
    }
}
