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
		NSMenuItem _myAttendanceMenuItem;
        AppDelegate _app;
        ViewController _controller;
        IScreeningProvider _screeningProvider;
        Film _film;
        Screening _screening;
        Dictionary<nint, string> _friendByTag;
        static Dictionary<nint, bool> _FilmScreeningEnabledByTag;
        static Dictionary<string, Screening> _filmScreeningByMenuItemTitle;
        #endregion

        #region Properties
        public Screening Screening => _screening;
        public static int FilmMenuHeaderItemTag => _filmMenuHeaderItemTag;
        public static FilmRatingDialogController FilmRatingController => ViewController.App.FilmsDialogController;
        #endregion

        #region Constructors
        public ScreeningMenuDelegate(AppDelegate app, NSMenuItem myAttendanceMenuItem)
        {
            _app = app;
            _controller = app.Controller;
            _myAttendanceMenuItem = myAttendanceMenuItem;
            _screeningMenu = _myAttendanceMenuItem.Menu;
            _FilmScreeningEnabledByTag = new Dictionary<nint, bool> { };
            _friendByTag = new Dictionary<nint, string> { };
            _filmScreeningByMenuItemTitle = new Dictionary<string, Screening> { };
            PopulateAttandanceMenuItems();
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
            if(currFilm != _film)
            {
                _film = currFilm;
                PopulateFilmMenuItems(menu);
            }

            // Get the current screening.
            var currScreening = _screeningProvider.CurrentScreening;
            if (currScreening != _screening)
            {
                _screening = currScreening;
                PopulateFilmMenuItems(menu);
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
                    // Take action on the menu tag and the friends dictionary.
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
            if (_friendByTag.ContainsKey(item.Tag))
            {
				var friend = _friendByTag[item.Tag];
                if (FilmRatingViewRunning())
                {
                    item.State = NSCellStateValue.Off;
                    item.Enabled = false;
                }
                else
                {
                    item.State = _screening.FriendAttends(friend) ? NSCellStateValue.On : NSCellStateValue.Off;
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
                    item.Enabled = _screening != null;
                    item.State = (_screening != null && _screening.SoldOut) ? NSCellStateValue.On : NSCellStateValue.Off;
                    break;
                case _ticketsBoughtMenuItemTag:
                    item.Enabled = _screening != null;
                    item.State = (_screening != null && _screening.TicketsBought) ? NSCellStateValue.On : NSCellStateValue.Off;
                    break;
                case _myAttendanceMenuItemTag:
					item.Title = ScreeningStatus.Me;
                    item.Enabled = _screening != null;
                    item.State = (_screening != null && _screening.IAttend) ? NSCellStateValue.On : NSCellStateValue.Off;
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

        void PopulateAttandanceMenuItems()
        {
			_myAttendanceMenuItem.Title = ScreeningStatus.Me;
            var menu = _myAttendanceMenuItem.Menu;
            var anchorIndex = menu.IndexOf(_myAttendanceMenuItem);
            foreach (var friend in ScreeningStatus.MyFriends)
            {
                var friendNumber = ScreeningStatus.MyFriends.IndexOf(friend) + 1;
                var item = new NSMenuItem(friend)
                {
                    Action = new Selector("ToggleFriendAttendance:"),
                    Tag = _myAttendanceMenuItemTag + friendNumber,
                    KeyEquivalent = friendNumber.ToString()
                };
                menu.InsertItem(item, anchorIndex + friendNumber);
                _friendByTag.Add(item.Tag, friend);
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
        void PopulateFilmMenuItems(NSMenu menu)
        {
            // Remove the existing screening items from the menu.
            foreach (var item in _filmScreeningByMenuItemTitle.Keys)
            {
                menu.RemoveItem(menu.ItemWithTitle(item));
            }

            // Add the screenings with same film to the Screening menu.
            int screeningNumber = 0;
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
                    Tag = FilmMenuHeaderItemTag + screeningNumber,
                    State = NSCellStateValue.Off,
                    KeyEquivalent = screeningNumber.ToString(),
                    KeyEquivalentModifierMask = NSEventModifierMask.AlternateKeyMask | NSEventModifierMask.CommandKeyMask
                };
                //item.Activated += _screeningProvider.GoToScreening;
				menu.AddItem(item);
                _FilmScreeningEnabledByTag.Add(item.Tag, screening != _screening);
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
            _screening = null;
        }
        #endregion
    }
}
