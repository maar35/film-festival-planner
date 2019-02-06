using System;
using AppKit;
using Foundation;
using System.Linq;
using System.Collections.Generic;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// View controller, manages the main window, which contains one TableView
    /// to display the screenings of one festival day.
    /// </summary>

    public partial class ViewController : NSViewController, IScreeningProvider
    {
        #region Private Members
        ScreeningsPlan _plan = null;
        ScreeningsTableView _mainView = null;
        Dictionary<Screen, Dictionary<Screening, ScreeningControl>> _screeningControls;
        NSMenuItem _clickableLabelsMenuItem = null;
        #endregion

        #region Application Access
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public ScreeningsPlan Plan => _plan;
        public NSTableView TableView => ScreeningsTable;
        internal int RunningPopupsCount { get; set; } = 0;
        #endregion
        
        #region Computed Properties
        internal NSMenuItem ClickableLabelsMenuItem
        {
            set
            {
                _clickableLabelsMenuItem = value;
                SetClickableLabelsMenuItemState();
            }
        }

        bool ScreeningSelected
        {
            set => _screeningControls[_plan.CurrScreening.Screen][_plan.CurrScreening].Selected = value;
        }

        public override NSObject RepresentedObject
        {
            get
            {
                return base.RepresentedObject;
            }
            set
            {
                base.RepresentedObject = value;
                // Update the view, if already loaded.
            }
        }
        #endregion

        #region Interface Implementation Properties
        public Screening CurrentScreening => _plan.CurrScreening;
        public List<Screening> Screenings => FilmScreenings(_plan.CurrScreening.FilmId);
        public Film CurrentFilm => this.GetFilmById(CurrentScreening.FilmId);
        #endregion

        #region Contructors
        public ViewController(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Override Methods
        public override void ViewDidLoad()
        {
            base.ViewDidLoad();

            // Do any additional setup after loading the view.
            DisposeColorLabels();
            _plan = new ScreeningsPlan();
            _mainView = new ScreeningsTableView(this, ScreensColumn, ScreeningsColumn);
            InitializeScreeningControls();
        }

        public override void AwakeFromNib()
        {
            base.AwakeFromNib();

            // Set the header text of the columns.
            _plan = new ScreeningsPlan();
            _mainView = new ScreeningsTableView(this, ScreensColumn, ScreeningsColumn);
            _mainView.DrawHeaders(_plan);

            // Create the Screening Table Data Source and populate it
            var screeningTableDataSource = new ScreeningsTableDataSource();
            screeningTableDataSource.Plan = _plan;

            // Populate the table view
            TableView.DataSource = screeningTableDataSource;
            TableView.Delegate = new ScreeningsTableDelegate(screeningTableDataSource, _mainView.ScreeningsView);
            TableView.AllowsMultipleSelection = false;
            TableView.SelectionHighlightStyle = NSTableViewSelectionHighlightStyle.Regular;
            TableView.UsesAlternatingRowBackgroundColors = true;
        }

        public override void PrepareForSegue(NSStoryboardSegue segue, NSObject sender)
        {
            base.PrepareForSegue(segue, sender);

            // Take action based on the segue name.
            switch (segue.Identifier)
            {
                case "ModalSegue":
                    var dialog = segue.DestinationController as ScreeningDialogController;
                    dialog.PopulateDialog((ScreeningControl)sender);
                    dialog.AttendanceChanged += (s, e) => dialog.ToggleMyAttandance();
                    dialog.DialogAccepted += (s, e) => TableView.DeselectRow(TableView.SelectedRow);
                    dialog.DialogCanceled += (s, e) => TableView.DeselectRow(TableView.SelectedRow);
                    dialog.Presentor = this;
                    break;
            }
        }

        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            App.Controller = this;
        }

        public override void ViewWillDisappear()
        {
            base.ViewDidDisappear();

            App.Controller = null;
        }
        #endregion

        #region Private Methods
        void SetClickableLabelsMenuItemState()
        {
            _clickableLabelsMenuItem.State = GetNSCellStateValue(ScreeningControl.UseCoreGraphics);
        }

        void DisplayScreeningsView()
        {
            _mainView.HeadersView.DrawCurrDay(_plan);
            InitializeScreeningControls();
            ReloadScreeningsView();
        }

        void InitializeScreeningControls()
        {
            _screeningControls = new Dictionary<Screen, Dictionary<Screening, ScreeningControl>> { };
        }

        void DisposeColorLabels()
        {
            BlackLabel.RemoveFromSuperview();
            GreyLabel.RemoveFromSuperview();
            BlueLabel.RemoveFromSuperview();
            RedLabel.RemoveFromSuperview();
            BlackLabel.Dispose();
            GreyLabel.Dispose();
            BlueLabel.Dispose();
            RedLabel.Dispose();
        }
        #endregion

        #region Private Screening Status methods
        void UpdateOneAttendanceStatus(Screening screening)
        {
            if (screening.IAttend)
            {
                if (screening.TicketsBought)
                {
					screening.Status = ScreeningStatus.Status.Attending;
                }
                else
                {
                    screening.Status = ScreeningStatus.Status.NeedingTickets;
                }
            }
            else if (screening.AttendingFriends.Count() > 0)
            {
                screening.Status = ScreeningStatus.Status.AttendedByFriend;
            }
            else if (TimesIAttendFilm(screening) > 0)
            {
                screening.Status = ScreeningStatus.Status.AttendingFilm;
            }
            else if (HasTimeOverlap(screening))
            {
                screening.Status = ScreeningStatus.Status.TimeOverlap;
            }
            else
            {
                screening.Status = ScreeningStatus.Status.Free;
            }

            UpdateWarning(screening);
        }

        int TimesIAttendFilm(Screening screening)
        {
            var timesIAttendFilm = (
                from Screening s in _plan.Screenings
                where s.FilmId == screening.FilmId && s.IAttend
                select s
            ).Count();
            return timesIAttendFilm;
        }

        List<Screening> OverlappingAttendedScreenings(Screening screening)
        {
            var overlappingAttendedScreenings = (
                from Screening s in _plan.Screenings
                where s.IAttend
                    && s.StartTime <= screening.EndTime
                    && s.EndTime >= screening.StartTime
                select s
            ).ToList();
            return overlappingAttendedScreenings;
        }

        List<Screening> OverlappingScreenings(Screening screening)
        {
            var overlappingScreenings = (
                from Screening s in _plan.Screenings
                where s.StartTime <= screening.EndTime
                    && s.EndTime >= screening.StartTime
                    && s.FilmId != screening.FilmId
                select s
            ).ToList();
            return overlappingScreenings;
        }

        List<Screening> ScreeningsWithSameFilm(Screening screening)
        {
            var screeningsWithSameFilm = (
                from Screening s in _plan.Screenings
                where s.FilmId == screening.FilmId
                select s
            ).ToList();
            return screeningsWithSameFilm;
		}

        bool HasTimeOverlap(Screening screening)
        {
            return OverlappingAttendedScreenings(screening).Count() > 0;
        }
        #endregion

        #region Public Methods
        public bool ViewIsActive()
        {
            return RunningPopupsCount == 0;
        }

        public void ReloadScreeningsView()
        {
            TableView.ReloadData();
            TableView.ScrollRowToVisible(_plan.CurrDayScreens.IndexOf(_plan.CurrScreen));
        }

        public void AddScreenToScreeningControls(Screen screen)
        {
            if (_screeningControls.ContainsKey(screen))
            {
                _screeningControls.Remove(screen);
            }
            _screeningControls.Add(screen, new Dictionary<Screening, ScreeningControl> { });
        }

        public void AddScreeningControl(Screen screen, Screening screening, ScreeningControl control)
        {
            if (_screeningControls[screen].ContainsKey(screening))
            {
                _screeningControls[screen].Remove(screening);
            }
            _screeningControls[screen].Add(screening, control);
        }

        public List<Screening> FilmScreenings(int filmId)
        {
            var filmScreenings = (
                from Screening screening in _plan.Screenings
                where screening.FilmId == filmId
                orderby screening.StartTime
                select screening
            ).ToList();
            return filmScreenings;
        }

        public List<Screening> FilmScreenings(Screening screening)
        {
            var filmScreenings = (
                from Screening s in _plan.Screenings
                where s.FilmId == screening.FilmId
                orderby s.StartTime
                select s
            ).ToList();
            return filmScreenings;
        }

        public Film GetFilmById(int filmId)
        {
            return _plan.Films.First(f => f.FilmId == filmId);
        }

        public FilmRating GetFriendFilmRating(int filmId, string friend)
        {
            var ratings = _plan.FriendFilmRatings.Where(r => r.FilmId == filmId).Where(r => r.Friend == friend);
            if (ratings.ToList().Count == 0)
            {
                return FilmRating.Unrated;
            }
            return ratings.First().Rating;
        }

        public void SetFriendFilmRating(int filmId, string friend, FilmRating rating)
        {
            var friendRatings = _plan.FriendFilmRatings.Where(r => r.FilmId == filmId).Where(r => r.Friend == friend);
            if (friendRatings.ToList().Count == 0)
            {
                if(!rating.IsUnrated)
                {
                    _plan.FriendFilmRatings.Add(new FriendFilmRating(filmId, friend, rating));
                }
            }
            else
            {
                FriendFilmRating friendFilmRating = friendRatings.First();
                if (rating.IsUnrated)
                {
                    _plan.FriendFilmRatings.Remove(friendFilmRating);
                }
                else
                {
                    friendFilmRating.Rating = rating;
                }
            }
        }

        public FilmRating GetFilmFanRating(Film film, string filmFan)
        {
            FilmRating rating;
            if (filmFan == ScreeningStatus.Me)
            {
                rating = film.Rating;
            }
            else
            {
                rating = GetFriendFilmRating(film.FilmId, filmFan);
            }
            return rating;
        }

        public void UpdateAttendanceStatus(Screening screening)
        {
            UpdateOneAttendanceStatus(screening);

            var overlappingScreenings = OverlappingScreenings(screening);
            foreach (Screening overlappingScreening in overlappingScreenings)
            {
                UpdateOneAttendanceStatus(overlappingScreening);
            }

            var screeningsWithSameFilm = ScreeningsWithSameFilm(screening);
            foreach (Screening screeningWithSameFilm in screeningsWithSameFilm)
            {
                UpdateOneAttendanceStatus(screeningWithSameFilm);
            }
        }

        public void UpdateWarning(Screening screening)
        {
            if (TimesIAttendFilm(screening) > 1)
            {
                screening.Warning = ScreeningStatus.Warning.SameMovie;
            }
            else if (screening.IAttend && OverlappingAttendedScreenings(screening).Count() > 1)
            {
                screening.Warning = ScreeningStatus.Warning.TimeOverlap;
            }
            else
            {
                screening.Warning = ScreeningStatus.Warning.NoWarning;
            }
        }

        static public NSCellStateValue GetNSCellStateValue(bool shouldBeOn)
        {
            return shouldBeOn ? NSCellStateValue.On : NSCellStateValue.Off;
        }
        #endregion

        #region Public Action Methods
        public void ToggleClickableLabels()
        {
            ScreeningControl.UseCoreGraphics = !ScreeningControl.UseCoreGraphics;
            SetClickableLabelsMenuItemState();
            DisplayScreeningsView();
        }

        public void GoToDay(DateTime day)
        {
            int numberOfDaysFromCurrent = (day - _plan.CurrDay).Days;
            SetNextDay(numberOfDaysFromCurrent);
        }

        public void SetNextDay(int days)
        {
			_plan.SetNextDay(days);
            DisplayScreeningsView();
        }

        public void SetNextScreen(int numberOfScreens)
        {
			ScreeningSelected = false;
            _plan.SetNextScreen(numberOfScreens);
            ScreeningSelected = true;
        }

        public void SetNextScreening()
        {
            ScreeningSelected = false;
            _plan.SetNextScreening();
            ScreeningSelected = true;
        }

        public void SetPreviousScreening()
        {
            ScreeningSelected = false;
            _plan.SetPrevScreening();
			ScreeningSelected = true;
        }

        public void GoToScreening(Screening screening)
        {
            _plan.SetCurrScreening(screening);
            DisplayScreeningsView();
            TableView.Display();
            ScreeningControl control = _screeningControls[screening.Screen][screening];
            PerformSegue("ModalSegue", control);
        }

        public void ShowScreeningInfo()
        {
            Screening screening = _plan.CurrScreening;
            ScreeningControl control = _screeningControls[screening.Screen][screening];
            PerformSegue("ModalSegue", control);
        }

        public void ToggleTicketsBought()
        {
            Screening screening = _plan.CurrScreening;
            screening.TicketsBought = !screening.TicketsBought;
            UpdateAttendanceStatus(screening);
            ReloadScreeningsView();
        }

        public void ToggleSoldOut()
        {
            Screening screening = _plan.CurrScreening;
			screening.SoldOut = !screening.SoldOut;
            UpdateAttendanceStatus(screening);
            ReloadScreeningsView();
        }

        public void ToggleMyAttendance()
        {
            Screening screening = _plan.CurrScreening;
            screening.ToggleMyAttendance();
            UpdateAttendanceStatus(screening);
            ReloadScreeningsView();
        }

        public void ToggleFriendAttendance(string friend)
        {
            Screening screening = _plan.CurrScreening;
            screening.ToggleFriendAttendance(friend);
            UpdateAttendanceStatus(screening);
            ReloadScreeningsView();
        }

        public void DownloadFilmInfo(NSObject sender)
        {
            //// Create new window
            //var storyboard = NSStoryboard.FromName("Main", null);
            //var controller = storyboard.InstantiateControllerWithIdentifier("MainWindow") as NSWindowController;

            //// Display
            //controller.ShowWindow(this);

            //// Set the title
            //controller.Window.Title = "Download Film Info";

            App.FilmsDialogController?.PerformSegue("DownloadFilmInfoSegue", sender);
        }

        [Action("ShowFilmRatings:")]
        internal void ShowFilmRating(NSObject sender)
        {
            PerformSegue("FilmRatingSegue", sender);
        }

        //[Action("DownloadFilmInfo:")]
        //internal void DownloadFilmInfo(NSObject sender)
        //{
        //    PerformSegue("DownloadFilmInfoSegue", sender);
        //}
        #endregion
    }
}
