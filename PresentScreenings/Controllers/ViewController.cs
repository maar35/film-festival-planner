using System;
using AppKit;
using Foundation;
using System.Linq;
using System.Collections.Generic;
using System.Text;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// View controller, manages the main window, which contains one TableView
    /// to display the screenings of one festival day.
    /// </summary>

    public partial class ViewController : GoToScreeningDialog, IScreeningProvider
    {
        #region Private Members
        private TimeSpan _pause = AppDelegate.PauseBetweenOnDemandScreenings;
        private ScreeningsPlan _plan = null;
        private ScreeningsTableView _mainView = null;
        private Dictionary<Screening, ScreeningControl> _controlByScreening;
        private NSMenuItem _clickableLabelsMenuItem = null;
        #endregion

        #region Application Access
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public ScreeningsPlan Plan => _plan;
        public NSTableView TableView => ScreeningsTable;
        internal ScreeningDialogController ScreeningInfoDialog { get; set; }
        internal int RunningPopupsCount { get; set; } = 0;
        public static TimeSpan DaySpan => new TimeSpan(24, 0, 0);
        public static TimeSpan EarliestTime => new TimeSpan(ScreeningsTableView.FirstDisplayedHour, 0, 0);
        public static TimeSpan LatestTime => new TimeSpan(ScreeningsTableView.LastDisplayedHour - 1, 59, 0);
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

        private bool ScreeningSelected
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
        public List<Screening> Screenings => _plan.CurrScreening.FilmScreenings;
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
            _plan = new ScreeningsPlan(AppDelegate.DocumentsFolder);

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

        public override void ViewDidAppear()
        {
            base.ViewDidAppear();
            SetWindowTitle();
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
                    filmInfoDialog.UseTitleBackground = true;
                    FilmInfoDialogController.Presentor = this;
                    break;
            }
        }

        public override void GoToScreening(Screening screening)
        {
            SetCurrScreening(screening);
            ScreeningControl control = _controlByScreening[screening];
            PerformSegue("ScreeningsToScreeningInfo:", control);
        }
        #endregion

        #region Private Methods
        private void SetCurrScreening(Screening screening)
        {
            _plan.SetCurrScreening(screening);
            DisplayScreeningsView();
            TableView.Display();
            TableView.ScrollRowToVisible(_plan.CurrDayScreens.IndexOf(screening.Screen));
        }

        private void SetClickableLabelsMenuItemState()
        {
            _clickableLabelsMenuItem.State = GetNSCellStateValue(ScreeningControl.UseCoreGraphics);
        }

        private void DisplayScreeningsView()
        {
            _mainView.HeadersView.DrawCurrDay(_plan);
            SetWindowTitle();
            InitializeScreeningControls();
            ReloadScreeningsView();
        }

        private void InitializeScreeningControls()
        {
            _controlByScreening = new Dictionary<Screening, ScreeningControl> { };
        }

        private void DisposeColorLabels()
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
        private void UpdateOneAttendanceStatus(Screening screening)
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

        private List<Screening> ScreeningsWithSameFilm(Screening screening)
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

        public static bool ScreeningFitsAvailability(Screening screening, string fan=null)
        {
            // Take me as the default film fan.
            if (fan == null)
            {
                fan = ScreeningInfo.Me;
            }

            // Check film fan availability at the screening's start date.
            var fits = ScreeningsPlan.Availabilities
                .Where(a => a.Equals(fan, screening.StartDate))
                .Any();

            return fits;
        }

        public void SetWindowTitle()
        {
            var availableFans = ScreeningsPlan.Availabilities
                .Where(a => a.Equals(a.FilmFan, Plan.CurrDay))
                .Select(a => a.FilmFan)
                .ToList();
            string sep = ", ";
            string available = availableFans.Count > 0 ? $"{string.Join(sep, availableFans)}" : "No fans available";
            View.Window.Title = $"{AppDelegate.Festival} {AppDelegate.FestivalYear} - {Plan.CurrDay:ddd d MMM} - {available}";
        }

        public List<Screening> DayScreenings()
        {
            var dayScreenings = ScreeningsPlan.Screenings
                .Where(s => s.StartDate == Plan.CurrDay)
                .ToList();
            return dayScreenings;
        }

        public bool ViewIsActive()
        {
            return RunningPopupsCount == 0;
        }

        public void ReloadScreeningsView()
        {
            TableView.ReloadData();
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
        public static void ReportDuplicateScreenings()
        {
            var screeningComparer = new ScreeningEqualityComparer();
            var existsByScreening = new Dictionary<Screening, bool>(screeningComparer);
            var removedScreenings = new List<Screening> { };
            var screenings = ScreeningsPlan.Screenings.Where(s => s.Location);
            foreach (var screening in screenings)
            {
                if (existsByScreening.ContainsKey(screening))
                {
                    removedScreenings.Add(screening);
                }
                else
                {
                    existsByScreening.Add(screening, true);
                }
            }
            if (removedScreenings.Count > 0)
            {
                string line = Environment.NewLine;
                string title = "Duplicate Screenings Found";
                StringBuilder builder = new StringBuilder($"Duplicate screenings:{line}{line}");
                builder.AppendJoin<Screening>($",{line}", removedScreenings);
                AlertRaiser.RunInformationalAlert(title, builder.ToString());
            }
        }

        public static void ReportCoincidingScreeninings()
        {
            var screeningsByCoincideKey = new Dictionary<string, List<Screening>> { };
            var screenings = ScreeningsPlan.Screenings.Where(s => s.Location);
            foreach (var screening in screenings)
            {
                string key = screening.CoincideKey;
                if (!screeningsByCoincideKey.Keys.Contains(key))
                {
                    screeningsByCoincideKey.Add(key, new List<Screening> { });
                }
                screeningsByCoincideKey[key].Add(screening);
            }
            string line = Environment.NewLine;
            var coinciders = screeningsByCoincideKey
                .Where(pair => pair.Value.Count > 1)
                .Select(pair => $"{line}{pair.Key}:{line}{string.Join(',' + line, pair.Value.Select(s => s.ScreeningTitle))}");
            if (coinciders.Count() > 0)
            {
                string title = "Coinciding Screenings Found";
                StringBuilder builder = new StringBuilder($"Coinciding screenings:{line}");
                builder.AppendJoin(line, coinciders);
                AlertRaiser.RunInformationalAlert(title, builder.ToString(), true);
            }
        }

        public static List<Screening> FilmScreenings(int filmId)
        {
            var filmScreenings = (
                from Screening screening in ScreeningsPlan.Screenings
                where screening.FilmId == filmId && (AppDelegate.VisitPhysical || screening is OnDemandScreening || screening is OnLineScreening)
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
            var info = ScreeningsPlan.ScreeningInfos.Where(s => s.OriginalFilmId == filmId && s.Screen == screen && s.StartTime == startTime).ToList();
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
                string informativeText = $"'{ex.Message}' is not a valid rating.\n{filmFan}'s rating of '{GetFilmById(filmId)}' remains {oldRatingString}.";
                AlertRaiser.RunInformationalAlert("Rating Not Changed", informativeText);
            }
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
            UpdateOneAttendanceStatus(OverlappingScreenings(screening, true));
            UpdateOneAttendanceStatus(ScreeningsWithSameFilm(screening));
        }

        public void UpdateOneAttendanceStatus(List<Screening> screenings)
        {
            foreach (var screening in screenings)
            {
                UpdateOneAttendanceStatus(screening);
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

        #region Methods working with movable screenings
        private void MoveOnDemandScreening(OnDemandScreening onDemandScreening, TimeSpan span)
        {
            var oldOverlappers = OverlappingScreenings(onDemandScreening, true);
            onDemandScreening.MoveStartTime(span);
            UpdateOneAttendanceStatus(oldOverlappers);
            Plan.InitializeDays();
            UpdateAttendanceStatus(onDemandScreening);
        }

        public TimeSpan GetSpanToAutomaticallyFit(Screening screening, bool forward = false)
        {
            Plan.SetCurrScreening(screening);
            return GetSpanToFit(screening, forward, true);
        }

        private TimeSpan GetSpanToFit(Screening screening, bool forward, bool automatic = false)
        {
            // Define helper functions.
            int increasingComparer(Screening one_s, Screening other_s) => one_s.EndTime.CompareTo(other_s.EndTime);
            int descendingComparer(Screening one_s, Screening other_s) => other_s.StartTime.CompareTo(one_s.StartTime);
            TimeSpan jointSpan(Screening earlier_s, Screening later_s) => later_s.EndTime - earlier_s.StartTime;
            TimeSpan distance(Screening one_s, Screening other_s)
            {
                Screening earlier_s = one_s.StartTime < other_s.StartTime ? one_s : other_s;
                Screening later_s = one_s.StartTime >= other_s.StartTime ? one_s : other_s;
                return later_s.StartTime - earlier_s.EndTime;
            }

            // Set variables depending on whether the screening moves forward or backward.
            int sign = forward ? 1 : -1;
            Func<Screening, bool> isBeyond;
            Func<Screening, TimeSpan> spanToMove;
            if (forward)
            {
                isBeyond = s => s.EndTime > screening.StartTime;
                spanToMove = s => jointSpan(screening, s) + _pause;
            }
            else
            {
                isBeyond = s => s.StartTime < screening.EndTime;
                spanToMove = s => -jointSpan(s, screening) - _pause;
            }

            // Find attended screenings that lay beyond the given one.
            var currDay = Plan.CurrDay;
            var attendedScreenings = DayScreenings()
                .Where(s => s.StartDate == currDay && isBeyond(s) && s.IAttend)
                .ToList();
            attendedScreenings.Remove(screening);
            if (forward)
            {
                attendedScreenings.Sort(increasingComparer);
            }
            else
            {
                attendedScreenings.Sort(descendingComparer);
            }

            // Find the first space where the given screening fits.
            var otherScreenings = new List<Screening> { };
            otherScreenings.AddRange(attendedScreenings);
            foreach (var attendedScreening in attendedScreenings)
            {
                otherScreenings.Remove(attendedScreening);
                if (otherScreenings.Count == 0)
                {
                    return spanToMove(attendedScreening);
                }
                var nextScreening = otherScreenings[0];
                if (distance(attendedScreening, nextScreening) >= screening.Duration + 2 * _pause)
                {
                    return spanToMove(attendedScreening);
                }
            }

            // Don't move further when beyond all attended screenings if moving
            // automatically.
            if (automatic)
            {
                return TimeSpan.Zero;
            }

            // Return the pause span when beyond all attended screenings.
            return sign * _pause;
        }

        public static bool MoveForwardAllowed(Screening screening, bool withinDay = false)
        {
            if (screening == null)
            {
                return false;
            }
            if (screening is OnDemandScreening onDemandScreening)
            {
                bool allowed = onDemandScreening.EndTime < onDemandScreening.WindowEndTime;
                if (allowed && withinDay)
                {
                    allowed = onDemandScreening.StartTime.TimeOfDay < LatestTime;
                }
                return allowed;
            }
            return false;
        }

        public static bool MoveBackwardAllowed(Screening screening, bool withinDay = false)
        {
            if (screening == null)
            {
                return false;
            }
            if (screening is OnDemandScreening onDemandScreening)
            {
                bool allowed = onDemandScreening.StartTime > onDemandScreening.WindowStartTime;
                if (allowed && withinDay)
                {
                    allowed = onDemandScreening.StartTime.TimeOfDay > EarliestTime;
                }
                return allowed;
            }
            return false;
        }

        public void MoveToWindowStart(OnDemandScreening onDemandScreening)
        {
            TimeSpan span = onDemandScreening.WindowStartTime - onDemandScreening.StartTime;
            MoveOnDemandScreening(onDemandScreening, span);
        }

        public void MoveToWindowEnd(OnDemandScreening onDemandScreening)
        {
            TimeSpan span = onDemandScreening.WindowEndTime - onDemandScreening.StartTime;
            MoveOnDemandScreening(onDemandScreening, span);
        }

        public void MoveOnDemandScreeningAutomatically(OnDemandScreening onDemandScreening, TimeSpan span)
        {
            MoveOnDemandScreening(onDemandScreening, span);
        }

        public bool TryMoveBackwardOverNight(OnDemandScreening onDemandScreening)
        {
            if (onDemandScreening.StartDate > onDemandScreening.WindowStartTime.Date)
            {
                DateTime newStartTime = onDemandScreening.StartDate - DaySpan + LatestTime;
                TimeSpan span = newStartTime - onDemandScreening.StartTime;
                MoveOnDemandScreening(onDemandScreening, span);
                //GoToDay(onDemandScreening.StartTime.Date);
                //SetCurrScreening(onDemandScreening);
                return true;
            }
            return false;
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
            _plan.CurrDay = day;
            DisplayScreeningsView();
            ScreeningInfoDialog?.UpdateAttendances();
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

        public static void VisitFilmWebsite(Film film)
        {
            string url = film.Url;
            NSWorkspace.SharedWorkspace.OpenUrl(new NSUrl(url));
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

        public void MoveScreening(bool forward, Screening screening = null)
        {
            // Apply the deafalt screening.
            if (screening == null)
            {
                screening = Plan.CurrScreening;
            }

            // Move the current screening to the nearest unattended space within the day.
            if (screening is OnDemandScreening onDemandScreening)
            {
                MoveOnDemandScreening(onDemandScreening, GetSpanToFit(onDemandScreening, forward));
                ScreeningInfoDialog?.UpdateAttendances();
                SetCurrScreening(onDemandScreening);
            }
        }

        public void MoveScreening24Hours(bool forward)
        {
            // Move the current screening one day into the given direction.
            if (Plan.CurrScreening is OnDemandScreening onDemandScreening)
            {
                MoveOnDemandScreening(onDemandScreening, forward ? DaySpan : -DaySpan);
                GoToDay(onDemandScreening.StartTime.Date);
                SetCurrScreening(onDemandScreening);
            }
        }

        [Action("ShowFilmRatings:")]
        internal void ShowFilmRating(NSObject sender)
        {
            PerformSegue("FilmRatingSegue", sender);
        }

        [Action("ShowFilmInfo:")]
        internal void ShowFilmInfo(NSObject sender)
        {
            PerformSegue("ScreeningsToFilmInfo", sender);
        }
        #endregion
    }
}
