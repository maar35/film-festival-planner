// This file has been autogenerated from a class added in the UI designer.

using System;
using Foundation;
using AppKit;
using System.Collections.Generic;
using System.Linq;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    public partial class FilmRatingDialogController : GoToScreeningDialog, IScreeningProvider
    {
        #region Private Variables
        ViewController _presentor;
        FilmTableDataSource _filmTableDataSource;
        #endregion

        #region Application Access
        static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public NSTableView FilmRatingTableView => _filmRatingTableView;
        public static bool TypeMatchFromBegin { get; set; } = true;
        public static bool OnlyFilmsWithScreenings { get; set; }
        public static TimeSpan MinimalDuration { get; set; }
        #endregion

        #region Interface Implementation Properties
        public Film CurrentFilm => GetSelectedFilm();
        public Screening CurrentScreening => null;
        public List<Screening> Screenings => GetScreeningsOfSelectedFilm();
        #endregion

        #region Constructors
        public FilmRatingDialogController(IntPtr handle) : base(handle)
        {
        }
        #endregion

        #region Override Methods
        public override void AwakeFromNib()
        {
            base.AwakeFromNib();

            _presentor = _app.Controller;
        }

        public override void ViewDidLoad()
        {
            base.ViewDidLoad();

            // Add friends rating colums to the table view.
            CreateFriendRatingColumns();

            // Polulate the controls
            _typeMatchMethodCheckBox.Action = new ObjCRuntime.Selector("ToggleTypeMatchMethod:");
            _combineTitlesButton.Action = new ObjCRuntime.Selector("SelectTitlesToCombine:");
            _uncombineTitleButton.Action = new ObjCRuntime.Selector("ShowTitlesToUncombine:");
            _goToScreeningButton.Action = new ObjCRuntime.Selector("ShowScreenings:");
            _downloadFilmInfoButton.Action = new ObjCRuntime.Selector("DownLoadInfoForOneFilm:");
            _doneButton.KeyEquivalent = ControlsFactory.EscapeKey;
            SetTypeMatchMethodControlStates();
        }

        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Create the Film Table Data Source and populate it
            _filmTableDataSource = new FilmTableDataSource(_app);
            SetFilmsWithScreenings();

            // Tell the app delegate we're alive.
            _app.FilmsDialogController = this;

            // Inactivate screenings view actions.
            _presentor.RunningPopupsCount++;

            // Initialize the controls.
            SetFilmRatingDialogButtonStates();

            // Populate the table view.
            _filmRatingTableView.DataSource = _filmTableDataSource;
            _filmRatingTableView.Delegate = new FilmTableDelegate(_filmTableDataSource, _presentor, this);
            _filmRatingTableView.AllowsMultipleSelection = true;
            _filmRatingTableView.AllowsColumnReordering = false;
            _filmRatingTableView.UsesAlternatingRowBackgroundColors = true;
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate we're gone.
            _app.FilmsDialogController = null;

            // Tell the main view controller we're gone.
            _presentor.RunningPopupsCount--;
        }

        public override void PrepareForSegue(NSStoryboardSegue segue, NSObject sender)
        {
            base.PrepareForSegue(segue, sender);

            // Take action based on the segue name
            switch (segue.Identifier)
            {
                case "CombineSheetSegue":
                    var combineSheet = segue.DestinationController as CombineTitlesSheetController;
                    combineSheet.SheetAccepted += (s, e) => CombineTitles((CombineTitlesEventArgs)e);
                    combineSheet.Presentor = this;
                    break;
                case "UncombineSheetSegue":
                    var uncombineSheet = segue.DestinationController as UncombineTitlesSheetController;
                    uncombineSheet.SheetAccepted += (s, e) => UncombineScreeningTitles((UncombineTitlesEventArgs)e);
                    uncombineSheet.Presentor = this;
                    break;
                case "GoToScreeningSegue":
                    FilmInfoDialogController.Presentor = this;
                    break;
                case "DownloadFilmInfoSegue":
                    var downloadFilmInfoController = segue.DestinationController as DownloadFilmInfoController;
                    downloadFilmInfoController.Presentor = this;
                    break;
            }
        }

        public override void GoToScreening(Screening screening)
        {
            _presentor.GoToScreening(screening);
            CloseDialog();
        }
        #endregion

        #region Private Methods
        void CreateFriendRatingColumns()
        {
            const float width = 60;
            foreach (string friend in ScreeningInfo.MyFriends)
            {
                var sortDescriptor = new NSSortDescriptor(friend, false, new ObjCRuntime.Selector("compare:"));
                var friendColumn = new NSTableColumn
                {
                    Title = friend,
                    Width = width,
                    MaxWidth = width,
                    Identifier = friend,
                    SortDescriptorPrototype = sortDescriptor
                };
                nint tag = ScreeningInfo.MyFriends.IndexOf(friend);
                _filmRatingTableView.AddColumn(friendColumn);
                CGRect frame = _filmRatingTableView.Frame;
                nfloat newRight = frame.X;
                _filmRatingTableView.AdjustPageWidthNew(ref newRight, frame.X, frame.X + width, frame.X + width);
                _filmRatingTableView.SortDescriptors.Append(sortDescriptor);
            }
        }

        void ToggleTypeMatchMethod()
        {
            TypeMatchFromBegin = !TypeMatchFromBegin;
            SetTypeMatchMethodControlStates();
        }

        void SetTypeMatchMethodControlStates()
        {
            _typeMatchMethodCheckBox.State = TypeMatchFromBegin ? NSCellStateValue.On : NSCellStateValue.Off;
            _app.ToggleTypeMatchMenuItem.State = TypeMatchFromBegin ? NSCellStateValue.On : NSCellStateValue.Off;
        }

        void SetFilmsWithScreenings()
        {
            List<Film> films = ScreeningsPlan.Films;
            if (OnlyFilmsWithScreenings)
            {
                _filmTableDataSource.Films = films.Where(f => GetScreeningsByFilmId(f.FilmId).Count > 0).ToList();
            }
            else
            {
                _filmTableDataSource.Films = films;
            }
        }

        void CombineTitles(CombineTitlesEventArgs e)
        {
            // Get the data from the event args.
            int mainFilmId = e.MainFilmId;
            List<int> filmIds = e.FilmIds;

            // Find the screenings that should get a new film ID.
            List<Screening> screeningsToGetNewFilmId = new List<Screening> { };
            List<Screening> screeningsToGetStatusUpdated = new List<Screening> { };
            foreach (var filmId in filmIds)
            {
                var screeningsOfFilm = GetScreeningsByFilmId(filmId);
                screeningsToGetStatusUpdated.AddRange(screeningsOfFilm);
                if (filmId != mainFilmId)
                {
                    screeningsToGetNewFilmId.AddRange(screeningsOfFilm.Where(s => s.FilmId != mainFilmId));
                }
            }

            // Update the screenings' film ID.
            foreach (var screening in screeningsToGetNewFilmId)
            {
                screening.FilmId = mainFilmId;
            }

            // Update the world outside.
            PropagateScreeningUpdates(screeningsToGetStatusUpdated);

            // Select the film with combined screenings.
            Film film = _filmTableDataSource.Films.First(f => f.FilmId == mainFilmId);
            int selectedRow = _filmTableDataSource.Films.IndexOf(film);
            _filmRatingTableView.SelectRow(selectedRow, true);
            _filmRatingTableView.ScrollRowToVisible(selectedRow);
        }

        void UncombineScreeningTitles(UncombineTitlesEventArgs e)
        {
            // Get the screenings from the event args.
            List<Screening> screenings = e.Screenings;

            // Find the original film ID of each distinct screening title.
            Dictionary<string, Film> titleToFilm = new Dictionary<string, Film> { };
            List<string> distinctTitles = (
                from Screening screening in screenings
                select screening.ScreeningTitle
            ).Distinct().ToList();
            foreach (var distinctTitle in distinctTitles)
            {
                Film film = GetFilmByTitle(distinctTitle);
                titleToFilm[distinctTitle] = film;
            }

            // Restore the original film ID in each of the given screenings.
            foreach (var screening in screenings)
            {
                Film originalFilm = titleToFilm[screening.ScreeningTitle];
                if (screening.FilmId != originalFilm.FilmId)
                {
                    screening.FilmId = originalFilm.FilmId;
                }
            }

            // Update the world outside.
            PropagateScreeningUpdates(screenings);

            // Select the uncombined films.
            NSMutableIndexSet rows = new NSMutableIndexSet();
            foreach (var film in titleToFilm.Values)
            {
                int row = _filmTableDataSource.Films.IndexOf(film);
                rows.Add(new NSIndexSet(row));
            }
            _filmRatingTableView.SelectRows(rows, false);
            _filmRatingTableView.ScrollRowToVisible((nint)rows.First());
        }

        void PropagateScreeningUpdates(List<Screening> screenings)
        {
            // Update the data source.
            SetFilmsWithScreenings();
            _filmRatingTableView.ReloadData();

            // Update the button states.
            SetFilmRatingDialogButtonStates();

            // Update the menu item states.
            _app.ScreeningMenuDelegate.ForceRepopulateFilmMenuItems();

            // Update the screening states.
            foreach (var screening in screenings)
            {
                _presentor.UpdateAttendanceStatus(screening);
            }
            _presentor.ReloadScreeningsView();
        }

        List<Screening> GetScreeningsOfSelectedFilm()
        {
            var screeningList = new List<Screening> { };
            if (OneFilmSelected())
            {
                screeningList = GetScreeningsByFilmId(GetSelectedFilm().FilmId);
            }
            return screeningList;
        }
        #endregion

        #region Public Methods
        public bool OneFilmSelected()
        {
            return _filmRatingTableView.SelectedRowCount == 1;
        }

        public bool MultipleFilmsSelected()
        {
            return _filmRatingTableView.SelectedRowCount > 1;
        }

        public bool OneOrMoreFilmsSelected()
        {
            return _filmRatingTableView.SelectedRowCount >= 1;
        }

        public void SetFilmRatingDialogButtonStates()
        {
            _combineTitlesButton.Enabled = MultipleFilmsSelected();
            _uncombineTitleButton.Enabled = OneFilmSelected();
            _goToScreeningButton.Enabled = OneFilmSelected();
            _downloadFilmInfoButton.Enabled = OneOrMoreFilmsSelected();
        }

        public Film GetSelectedFilm()
        {
            if (OneFilmSelected())
            {
                var filmIndex = FilmRatingTableView.SelectedRow;
                return GetFilmByIndex((nuint)filmIndex);
            }
            return null;
        }

        public Film GetFilmByIndex(nuint row)
        {
            return _filmTableDataSource.Films[(int)row];
        }

        public Film GetFilmById(int filmId)
        {
            return _filmTableDataSource.Films.First(f => f.FilmId == filmId);
        }

        public Film GetFilmByTitle(string title)
        {
            return ScreeningsPlan.Films.First(f => f.Title == title);
        }

        public List<Screening> GetScreeningsByFilmId(int filmId)
        {
            return ViewController.FilmScreenings(filmId);
        }

        public void CloseDialog()
        {
            _presentor.DismissViewController(this);
        }
        #endregion

        #region Custom Actions
        partial void AcceptDialog(Foundation.NSObject sender)
        {
            RaiseDialogAccepted();
            CloseDialog();
        }

        [Action("ToggleTypeMatchMethod:")]
        void ToggleTypeMatchMethod(NSObject sender)
        {
            ToggleTypeMatchMethod();
        }

        [Action("SelectTitlesToCombine:")]
        void SelectTitlesToCombine(NSObject sender)
        {
            PerformSegue("CombineSheetSegue", sender);
        }

        [Action("ShowTitlesToUncombine:")]
        void ShowTitlesToUncombine(NSObject sender)
        {
            PerformSegue("UncombineSheetSegue", sender);
        }

        [Action("ShowScreenings:")]
        void ShowScreenings(NSObject sender)
        {
            PerformSegue("GoToScreeningSegue", sender);
        }

        [Action("DownLoadInfoForOneFilm:")]
        void DownloadFilmInfo(NSObject sender)
        {
            PerformSegue("DownloadFilmInfoSegue", sender);
        }
        #endregion

        #region Events
        public EventHandler DialogAccepted;

        internal void RaiseDialogAccepted()
        {
            DialogAccepted?.Invoke(this, EventArgs.Empty);
        }
        #endregion
    }
}
