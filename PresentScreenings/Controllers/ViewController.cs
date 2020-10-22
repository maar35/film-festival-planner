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

    public partial class ViewController : GoToScreeningDialog, IScreeningProvider
    {
        #region Private Members
        ScreeningsPlan _plan = null;
        ScreeningsTableView _mainView = null;
        Dictionary<Screening, ScreeningControl> _controlByScreening;
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
            set => _controlByScreening[_plan.CurrScreening].Selected = value;
        }

        public override NSObject RepresentedObject
        {
            get => base.RepresentedObject;
            set => base.RepresentedObject = value;
        }
        #endregion

        #region Interface Implementation Properties
        public Screening CurrentScreening => _plan.CurrScreening;
        public List<Screening> Screenings => FilmScreenings(_plan.CurrScreening.FilmId);
        public Film CurrentFilm => GetFilmById(CurrentScreening.FilmId);
        #endregion

        #region Contructors
        public ViewController(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Override Methods

        /// <summary>
        /// Do any additional setup after loading the view.
        /// </summary>
        public override void ViewDidLoad()
        {
            base.ViewDidLoad();

            // Tell the application delegate we're alive.
            App.Controller = this;

            // Dispose the labels that only exist to store colors.
            DisposeColorLabels();

            // Create the screenings plan.
            _plan = new ScreeningsPlan(AppDelegate.Festival, AppDelegate.FestivalYear);

            // Create the screenings table view and draw the headers.
            _mainView = new ScreeningsTableView(this, ScreensColumn, ScreeningsColumn);
            _mainView.DrawHeaders(_plan);

            // Create the screening table data source and populate it
            var screeningTableDataSource = new ScreeningsTableDataSource();
            screeningTableDataSource.Plan = _plan;

            // Populate the table view
            TableView.DataSource = screeningTableDataSource;
            TableView.Delegate = new ScreeningsTableDelegate(screeningTableDataSource, _mainView.ScreeningsView);
            TableView.AllowsMultipleSelection = false;
            TableView.SelectionHighlightStyle = NSTableViewSelectionHighlightStyle.Regular;
            TableView.UsesAlternatingRowBackgroundColors = true;

            // Initialize the screening controls admin.
            InitializeScreeningControls();
        }

        public override void PrepareForSegue(NSStoryboardSegue segue, NSObject sender)
        {
            base.PrepareForSegue(segue, sender);

            // Take action based on the segue name.
            switch (segue.Identifier)
            {
                case "ScreeningsToScreeningInfo:":
                    var dialog = segue.DestinationController as ScreeningDialogController;
                    dialog.PopulateDialog((ScreeningControl)sender);
                    dialog.DialogAccepted += (s, e) => TableView.DeselectRow(TableView.SelectedRow);
                    dialog.DialogCanceled += (s, e) => TableView.DeselectRow(TableView.SelectedRow);
                    dialog.Presentor = this;
                    break;
                case "ScreeningsToFilmInfo":
                    var filmInfoDialog = segue.DestinationController as FilmInfoDialogController;
                    filmInfoDialog.DialogShouldClose = true;
                    FilmInfoDialogController.Presentor = this;
                    break;
            }
        }

        public override void GoToScreening(Screening screening)
        {
            _plan.SetCurrScreening(screening);
            DisplayScreeningsView();
            TableView.Display();
            TableView.ScrollRowToVisible(_plan.CurrDayScreens.IndexOf(screening.Screen));
            ScreeningControl control = _controlByScreening[screening];
            PerformSegue("ScreeningsToScreeningInfo:", control);
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
            _controlByScreening = new Dictionary<Screening, ScreeningControl> { };
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
                    screening.Status = ScreeningInfo.ScreeningStatus.Attending;
                }
                else
                {
                    screening.Status = ScreeningInfo.ScreeningStatus.NeedingTickets;
                }
            }
            else if (screening.AttendingFriends.Any())
            {
                screening.Status = ScreeningInfo.ScreeningStatus.AttendedByFriend;
            }
            else if (screening.TimesIAttendFilm > 0)
            {
                screening.Status = ScreeningInfo.ScreeningStatus.AttendingFilm;
            }
            else if (screening.HasTimeOverlap)
            {
                screening.Status = ScreeningInfo.ScreeningStatus.TimeOverlap;
            }
            else if (screening.HasNoTravelTime)
            {
                screening.Status = ScreeningInfo.ScreeningStatus.NoTravelTime;
            }
            else
            {
                screening.Status = ScreeningInfo.ScreeningStatus.Free;
            }

            UpdateWarning(screening);
        }

        List<Screening> ScreeningsWithSameFilm(Screening screening)
        {
            var screeningsWithSameFilm = (
                from Screening s in ScreeningsPlan.Screenings
                where s.FilmId == screening.FilmId
                select s
            ).ToList();
            return screeningsWithSameFilm;
        }
        #endregion

        #region Public Methods
        public static List<Screening> OverlappingScreenings(Screening screening, bool useTravelTime = false)
        {
            var overlappingScreenings = (
                from Screening s in ScreeningsPlan.Screenings
                where s.Overlaps(screening, useTravelTime) && s.FilmId != screening.FilmId
                select s
            ).ToList();
            return overlappingScreenings;
        }

        public static List<Screening> OverlappingAttendedScreenings(Screening screening, bool useTravelTime = false)
        {
            var overlappingAttendedScreenings = (
                from Screening s in ScreeningsPlan.Screenings
                where s.IAttend && s.Overlaps(screening, useTravelTime)
                select s
            ).ToList();
            return overlappingAttendedScreenings;
        }

        public bool ViewIsActive()
        {
            return RunningPopupsCount == 0;
        }

        public void ReloadScreeningsView()
        {
            TableView.ReloadData();
            if (App.AnalyserDialogController != null)
            {
                App.AnalyserDialogController.FilmOutlineView.ReloadData();
            }
        }

        public void AddScreeningControl(Screening screening, ScreeningControl control)
        {
            if (_controlByScreening.ContainsKey(screening))
            {
                _controlByScreening.Remove(screening);
            }
            _controlByScreening.Add(screening, control);
        }

        static public NSCellStateValue GetNSCellStateValue(bool shouldBeOn)
        {
            return shouldBeOn ? NSCellStateValue.On : NSCellStateValue.Off;
        }
        #endregion

        #region Public Methods working with ScreeningsPlan lists
        public static List<Screening> FilmScreenings(int filmId)
        {
            var filmScreenings = (
                from Screening screening in ScreeningsPlan.Screenings
                where screening.FilmId == filmId
                orderby screening.StartTime
                select screening
            ).ToList();
            return filmScreenings;
        }

        public static Film GetFilmById(int filmId)
        {
            return ScreeningsPlan.Films.First(f => f.FilmId == filmId);
        }

        public static FilmInfo GetFilmInfo(int filmId)
        {
            var info = ScreeningsPlan.FilmInfos.Where(f => f.FilmId == filmId).ToList();
            return info.Count > 0 ? info.First() : null;
        }

        public static bool FilmInfoIsAvailable(FilmInfo filmInfo)
        {
            return filmInfo != null && filmInfo.InfoStatus == Film.FilmInfoStatus.Complete;
        }

        public static bool FilmInfoIsAvailable(Film film)
        {
            return FilmInfoIsAvailable(GetFilmInfo(film.FilmId));
        }

        public static Film.FilmInfoStatus GetFilmInfoStatus(int filmId)
        {
            var info = GetFilmInfo(filmId);
            return info == null ? Film.FilmInfoStatus.Absent : info.InfoStatus;
        }

        public static ScreeningInfo GetScreeningInfo(int filmId, Screen screen, DateTime startTime)
        {
            var info = ScreeningsPlan.ScreeningInfos.Where(s => s.FilmId == filmId && s.Screen == screen && s.StartTime == startTime).ToList();
            return info.Count > 0 ? info.First() : null;
        }
        #endregion

        #region Public Methods working with Film Ratings
        public static FilmRating GetFilmFanFilmRating(int filmId, string filmFan)
        {
            var ratings = ScreeningsPlan.FilmFanFilmRatings.Where(r => r.FilmId == filmId).Where(r => r.FilmFan == filmFan);
            if (ratings.ToList().Count == 0)
            {
                return FilmRating.Unrated;
            }
            return ratings.First().Rating;
        }

        public static FilmRating GetFilmFanFilmRating(Film film, string filmFan)
        {
            FilmRating rating;
            rating = GetFilmFanFilmRating(film.FilmId, filmFan);
            return rating;
        }

        public void SetFilmFanFilmRating(int filmId, string filmFan, FilmRating rating)
        {
            var fanRatings = ScreeningsPlan.FilmFanFilmRatings.Where(r => r.FilmId == filmId).Where(r => r.FilmFan == filmFan);
            if (fanRatings.ToList().Count == 0)
            {
                if (!rating.IsUnrated)
                {
                    ScreeningsPlan.FilmFanFilmRatings.Add(new FilmFanFilmRating(filmId, filmFan, rating));
                }
            }
            else
            {
                FilmFanFilmRating filmFanFilmRating = fanRatings.First();
                if (rating.IsUnrated)
                {
                    ScreeningsPlan.FilmFanFilmRatings.Remove(filmFanFilmRating);
                }
                else
                {
                    filmFanFilmRating.Rating = rating;
                }
            }
        }

        public void SetRatingIfValid(NSTextField control, Func<string, string> GetControlValue, int filmId, string filmFan)
        {
            FilmRating rating = GetFilmFanFilmRating(filmId, filmFan);
            string oldRatingString = rating.Value;
            string newRatingString;
            try
            {
                newRatingString = GetControlValue(oldRatingString);
                if (newRatingString != oldRatingString)
                {
                    if (rating.SetRating(newRatingString))
                    {
                        SetFilmFanFilmRating(filmId, filmFan, rating);
                        ReloadScreeningsView();
                    }
                    else
                    {
                        control.StringValue = rating.Value;
                        throw new IllegalRatingException(newRatingString);
                    }
                }

            }
            catch (IllegalRatingException ex)
            {
                RunRatingNotChangedAlert(filmId, filmFan, oldRatingString, ex.Message);
                newRatingString = oldRatingString;
            }
        }

        public static void RunRatingNotChangedAlert(int filmId, string filmFan, string oldRatingString, string newRatingString)
        {
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Informational,
                InformativeText = $"'{newRatingString}' is not a valid rating.\n{filmFan}'s rating of '{GetFilmById(filmId)}' remains {oldRatingString}.",
                MessageText = $"Rating Not Changed",
            };
            alert.RunModal();
        }

        public static FilmRating GetMaxRating(Film film)
        {
            var ratings = ScreeningInfo.FilmFans.Select(f => GetFilmFanFilmRating(film, f));
            var rating = ratings.Max();
            return rating;
        }
        #endregion

        #region Public Methods working with Screening Attendance
        public void UpdateAttendanceStatus(Screening screening)
        {
            UpdateOneAttendanceStatus(screening);

            var overlappingScreenings = OverlappingScreenings(screening);
            foreach (Screening overlappingScreening in overlappingScreenings)
            {
                UpdateOneAttendanceStatus(overlappingScreening);
            }

            var noTravelTimeScreenings = OverlappingScreenings(screening, true);
            foreach (Screening noTravelTimeScreening in noTravelTimeScreenings)
            {
                UpdateOneAttendanceStatus(noTravelTimeScreening);
            }

            var screeningsWithSameFilm = ScreeningsWithSameFilm(screening);
            foreach (Screening screeningWithSameFilm in screeningsWithSameFilm)
            {
                UpdateOneAttendanceStatus(screeningWithSameFilm);
            }
        }

        public void UpdateWarning(Screening screening)
        {
            if (screening.TimesIAttendFilm > 1)
            {
                screening.Warning = ScreeningInfo.Warning.SameMovie;
            }
            else if (screening.IAttend && OverlappingAttendedScreenings(screening).Count() > 1)
            {
                screening.Warning = ScreeningInfo.Warning.TimeOverlap;
            }
            else
            {
                screening.Warning = ScreeningInfo.Warning.NoWarning;
            }
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

        public void ShowScreeningInfo()
        {
            Screening screening = _plan.CurrScreening;
            ScreeningControl control = _controlByScreening[screening];
            PerformSegue("ScreeningsToScreeningInfo:", control);
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

        public void ToggleAttendance(string filmfan)
        {
            Screening screening = _plan.CurrScreening;
            screening.ToggleFilmFanAttendance(filmfan);
            UpdateAttendanceStatus(screening);
            ReloadScreeningsView();
        }

        [Action("ShowFilmRatings:")]
        internal void ShowFilmRating(NSObject sender)
        {
            PerformSegue("FilmRatingSegue", sender);
        }

        [Action("TryShowFilmInfo:")]
        internal void TryShowFilmInfo(NSObject sender)
        {
            PerformSegue("ScreeningsToFilmInfo", sender);
        }
        #endregion
    }
}
