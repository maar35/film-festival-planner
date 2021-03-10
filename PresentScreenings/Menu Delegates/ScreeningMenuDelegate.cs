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
        private const int _showScreeningInfoMenuItemTag = 201;
        private const int _showFilmInfoMenuItemTag = 202;
        private const int _soldOutMenuItemTag = 203;
        private const int _ticketsBoughtMenuItemTag = 204;
        private const int _myAttendanceMenuItemTag = 210;
        private const int _moveBackwardMenuItemTag = 231;
        private const int _moveForwardMenuItemTag = 232;
        private const int _moveToPreviousDayMenuItemTag = 233;
        private const int _moveToNextDayMenuItemTag = 234;
        private const int _filmMenuHeaderItemTag = 400;
        #endregion

        #region Private Members
        private NSMenu _screeningMenu;
        private AppDelegate _app;
        private ViewController _controller;
        private IScreeningProvider _screeningProvider;
        private Film _film;
        readonly Dictionary<nint, string> _filmFanByTag;
        private static Dictionary<nint, bool> _FilmScreeningEnabledByTag;
        private static Dictionary<string, Screening> _filmScreeningByMenuItemTitle;
        #endregion

        #region Properties
        public Screening Screening { get; private set; }
        public static FilmRatingDialogController FilmRatingController => ViewController.App.FilmsDialogController;
        public static AnalyserDialogController AnalyserDialogController => ViewController.App.AnalyserDialogController;
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
            PopulateMoveMenuItems();
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
            _screeningProvider = FilmRatingViewRunning() ? (IScreeningProvider)FilmRatingController
                : AnalyserViewRunning() ? (IScreeningProvider)AnalyserDialogController
                : _controller;

            // Get the current film.
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
                // If one of some specific dialogs is running, all menu items must be inactive.
                if (DialogDisablesAllMenuItems())
                {
                    item.Enabled = false;
                    continue;
                }

                bool itemHandled = false;
                if (!itemHandled)
                {
                    // Take action based on the menu item tag and the film screenings dictionary.
                    itemHandled = FilmScreeningItemIsHandled(item);
                }
                if (!itemHandled)
                {
                    // Take action on the menu item tag and the film fan by tag dictionary.
                    itemHandled = AttendanceItemIsHandled(item);
                }
                if (!itemHandled)
                {
                    // Take action based on the menu item tag.
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
        private bool FilmScreeningItemIsHandled(NSMenuItem item)
        {
            if (_FilmScreeningEnabledByTag.ContainsKey(item.Tag))
            {
                item.Enabled = _FilmScreeningEnabledByTag[item.Tag];
                return true;
            }
            return false;
        }

        private bool AttendanceItemIsHandled(NSMenuItem item)
        {
            if (_filmFanByTag.ContainsKey(item.Tag))
            {
                var filmFan = _filmFanByTag[item.Tag];
                if (FilmRatingViewRunning() || AnalyserViewRunning())
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

        private bool ItemIsHandledByTag(NSMenuItem item)
        {
            bool itemHandled = true;
            bool enabled = Screening != null && !AnalyserViewRunning();
            switch (item.Tag)
            {
                case _showScreeningInfoMenuItemTag:
                    item.Enabled = _controller.ViewIsActive();
                    break;
                case _showFilmInfoMenuItemTag:
                    item.Enabled = enabled && _app.FilmInfoController == null;
                    break;
                case _soldOutMenuItemTag:
                    item.Enabled = enabled;
                    item.State = (Screening != null && Screening.SoldOut) ? NSCellStateValue.On : NSCellStateValue.Off;
                    break;
                case _ticketsBoughtMenuItemTag:
                    item.Enabled = enabled;
                    item.State = (Screening != null && Screening.TicketsBought) ? NSCellStateValue.On : NSCellStateValue.Off;
                    break;
                case _filmMenuHeaderItemTag:
                    item.Title = _film != null ? _film.Title : "No screening selected";
                    item.Enabled = false;
                    break;
                case _moveBackwardMenuItemTag:
                    item.Enabled = enabled && ViewController.MoveBackwardAllowed(Screening, true);
                    break;
                case _moveForwardMenuItemTag:
                    item.Enabled = enabled && ViewController.MoveForwardAllowed(Screening, true);
                    break;
                case _moveToPreviousDayMenuItemTag:
                    item.Enabled = enabled && ViewController.MoveBackwardAllowed(Screening);
                    break;
                case _moveToNextDayMenuItemTag:
                    item.Enabled = enabled && ViewController.MoveForwardAllowed(Screening);
                    break;
                default:
                    itemHandled = false;
                    break;
            }
            return itemHandled;
        }

        private void PopulateAttendanceMenuItems()
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

        private void PopulateMoveMenuItems()
        {
            _screeningMenu.AddItem(NSMenuItem.SeparatorItem);

            // Add the "move within day" menu items.
            _screeningMenu.AddItem(new NSMenuItem("Move backward")
            {
                Action = new Selector("MoveBackward:"),
                Tag = _moveBackwardMenuItemTag,
                KeyEquivalent = "[",
            });
            _screeningMenu.AddItem(new NSMenuItem("Move forward")
            {
                Action = new Selector("MoveForward:"),
                Tag = _moveForwardMenuItemTag,
                KeyEquivalent = "]",
            });

            // Add the "move over day" menu items.
            var altMask = NSEventModifierMask.AlternateKeyMask | NSEventModifierMask.CommandKeyMask;
            _screeningMenu.AddItem(new NSMenuItem("Move to previous day")
            {
                Action = new Selector("MoveToPreviousDay:"),
                Tag = _moveToPreviousDayMenuItemTag,
                KeyEquivalent = "[",
                KeyEquivalentModifierMask = altMask,
            });
            _screeningMenu.AddItem(new NSMenuItem("Move to next day")
            {
                Action = new Selector("MoveToNextDay:"),
                Tag = _moveToNextDayMenuItemTag,
                KeyEquivalent = "]",
                KeyEquivalentModifierMask = altMask,
            });
        }

        private void InitializeFilmMenuItems()
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
        private void PopulateFilmScreeningsMenuItems(NSMenu menu)
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
                bool enabled = (AnalyserViewRunning() || screening != Screening);
                _FilmScreeningEnabledByTag.Add(item.Tag, enabled);
                _filmScreeningByMenuItemTitle.Add(itemTitle, screening);
            }
        }

        private bool FilmRatingViewRunning()
        {
            return FilmRatingController != null;
        }

        private bool AnalyserViewRunning()
        {
            return AnalyserDialogController != null;
        }

        private bool DialogDisablesAllMenuItems()
        {
            return _app.AvailabilityDialogControler != null
                || _app.PlannerDialogController != null
                || _app.CombineTitleController != null
                || _app.UncombineTitleController != null;
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
