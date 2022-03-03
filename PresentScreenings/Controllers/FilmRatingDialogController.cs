// This file has been autogenerated from a class added in the UI designer.

using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    public partial class FilmRatingDialogController : GoToScreeningDialog, IScreeningProvider
    {
        #region Constants
        const float _descriptionWidth = 3000;
        const float _descriptionMaxWidth = 4000;
        const float _screeningCountWidth = 40;
        const float _screeningCountMaxWidth = 80;
        const float _subsectionWidth = 72;
        const float _subsectionMaxWidth = 200;
        const float _FilmFanRatingWidth = 60;
        #endregion

        #region Private Variables
        bool _textBeingEdited = false;
        ViewController _presentor;
        FilmTableDataSource _filmTableDataSource;
        Dictionary<bool, string> _titleByChanged;
        #endregion

        #region Properties
        public AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        public NSTableView FilmRatingTableView => _filmRatingTableView;
        public NSButton WebLinkButton => _downloadFilmInfoButton;
        public NSButton DoneButton => _closeButton;
        public bool TextBeingEdited
        {
            get => _textBeingEdited;
            set
            {
                _textBeingEdited = value;
                SetFilmRatingDialogButtonStates();
            }
        }
        public static bool TypeMatchFromBegin { get; set; } = true;
        public static bool OnlyFilmsWithScreenings { get; set; } = false;
        public static Subsection FilteredSubsection { get; set; } = null;
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
            _titleByChanged = new Dictionary<bool, string> { };
            _titleByChanged.Add(false, "Close");
            _titleByChanged.Add(true, "Save");
        }
        #endregion

        #region Override Methods
        public override void AwakeFromNib()
        {
            base.AwakeFromNib();

            _presentor = App.Controller;
        }

        public override void ViewDidLoad()
        {
            base.ViewDidLoad();

            // Add in-code created colums to the table view.
            CreateScreeningCountColumn();
            CreateSubsectionColumn();
            CreateFilmFanRatingColumns();
            CreateDescriptionColumn();

            // Polulate the controls
            _onlyFilmsWithScreeningsCheckBox.Action = new ObjCRuntime.Selector("ToggleOnlyFilmsWithScreenings:");
            _typeMatchMethodCheckBox.Action = new ObjCRuntime.Selector("ToggleTypeMatchMethod:");
            _combineTitlesButton.Action = new ObjCRuntime.Selector("SelectTitlesToCombine:");
            _uncombineTitleButton.Action = new ObjCRuntime.Selector("ShowTitlesToUncombine:");
            _goToScreeningButton.Action = new ObjCRuntime.Selector("ShowFilmInfo:");
            WebLinkButton.Action = new ObjCRuntime.Selector("VisitFilmWebsite:");
            DoneButton.KeyEquivalent = ControlsFactory.EscapeKey;
            DoneButton.StringValue = "Noot";
            SetOnlyFilmsWithScreeningsStates();
            SetTypeMatchMethodControlStates();
        }

        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Create the Film Table Data Source and populate it
            _filmTableDataSource = new FilmTableDataSource(App);
            SetFilmsWithScreenings();

            // Tell the app delegate we're alive.
            App.FilmsDialogController = this;

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
            _filmRatingTableView.SelectionHighlightStyle = NSTableViewSelectionHighlightStyle.Regular;
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate we're gone.
            App.FilmsDialogController = null;

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
            }
        }

        public override void GoToScreening(Screening screening)
        {
            _presentor.GoToScreening(screening);
            CloseDialog();
        }
        #endregion

        #region Private Methods
        private void CreateScreeningCountColumn()
        {
            CreateColumn("#Screenings", _screeningCountWidth, _screeningCountMaxWidth);
        }

        private void CreateSubsectionColumn()
        {
            CreateColumn("Subsection", _subsectionWidth, _subsectionMaxWidth);
        }

        private void CreateFilmFanRatingColumns()
        {
            const float width = _FilmFanRatingWidth;
            foreach (string filmFan in ScreeningInfo.FilmFans)
            {
                CreateColumn(filmFan, width, width);
            }
        }

        private void CreateDescriptionColumn()
        {
            CreateColumn("Description", _descriptionWidth, _descriptionMaxWidth);
        }

        private void CreateColumn(string title, float width, float maxWidth)
        {
            var sortDescriptor = new NSSortDescriptor(title, false, new ObjCRuntime.Selector("compare:"));
            var newColumn = new NSTableColumn
            {
                Title = title,
                Width = width,
                MaxWidth = maxWidth,
                Identifier = title,
                SortDescriptorPrototype = sortDescriptor
            };
            _filmRatingTableView.AddColumn(newColumn);
            CGRect frame = _filmRatingTableView.Frame;
            nfloat newRight = frame.X;
            _filmRatingTableView.AdjustPageWidthNew(ref newRight, frame.X, frame.X + frame.Width + width, frame.X + maxWidth);
            _filmRatingTableView.SortDescriptors.Append(sortDescriptor);
        }

        private void SetOnlyFilmsWithScreeningsStates()
        {
            _onlyFilmsWithScreeningsCheckBox.State = OnlyFilmsWithScreenings ? NSCellStateValue.On : NSCellStateValue.Off;
            App.ToggleOnlyFilmsWithScreeningsMenuItem.State = OnlyFilmsWithScreenings ? NSCellStateValue.On : NSCellStateValue.Off;
        }

        private void ToggleTypeMatchMethod()
        {
            TypeMatchFromBegin = !TypeMatchFromBegin;
            SetTypeMatchMethodControlStates();
        }

        private void SetTypeMatchMethodControlStates()
        {
            _typeMatchMethodCheckBox.State = TypeMatchFromBegin ? NSCellStateValue.On : NSCellStateValue.Off;
            App.ToggleTypeMatchMenuItem.State = TypeMatchFromBegin ? NSCellStateValue.On : NSCellStateValue.Off;
        }

        private void SetFilmsWithScreenings()
        {
            List<Film> films = ScreeningsPlan.Films;
            if (OnlyFilmsWithScreenings)
            {
                _filmTableDataSource.Films = films
                    .Where(f => f.FilmScreenings.Count > 0)
                    .ToList();
            }
            else
            {
                _filmTableDataSource.Films = films;
            }
        }

        private void FilterSubSection()
        {
            List<Film> films = ScreeningsPlan.Films;
            if (FilteredSubsection != null)
            {
                _filmTableDataSource.Films = films
                    .Where(f => f.Subsection != null)
                    .Where(f => f.Subsection.SubsectionId == FilteredSubsection.SubsectionId)
                    .ToList();
            }
            else
            {
                _filmTableDataSource.Films = films;
            }
        }

        private void CombineTitles(CombineTitlesEventArgs e)
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

        private void UncombineScreeningTitles(UncombineTitlesEventArgs e)
        {
            // Get the screenings from the event args.
            List<Screening> screenings = e.Screenings;

            // Restore the original film ID in each of the given screenings.
            foreach (var screening in screenings)
            {
                screening.FilmId = screening.OriginalFilmId;
            }

            // Update the world outside.
            PropagateScreeningUpdates(screenings);

            // Select the uncombined films.
            var filmIds = screenings
                .Select(s => s.FilmId)
                .Distinct();
            SelectFilms(filmIds.Select(f => ViewController.GetFilmById(f)).ToList());
        }

        private void PropagateScreeningUpdates(List<Screening> screenings)
        {
            // Update the data source.
            SetFilmsWithScreenings();
            _filmRatingTableView.ReloadData();

            // Update the button states.
            SetFilmRatingDialogButtonStates();

            // Update the menu item states.
            App.ScreeningMenuDelegate.ForceRepopulateFilmMenuItems();

            // Update the screening states.
            foreach (var screening in screenings)
            {
                _presentor.UpdateAttendanceStatus(screening);
            }
            _presentor.ReloadScreeningsView();
        }

        private List<Screening> GetScreeningsOfSelectedFilm()
        {
            var screeningList = new List<Screening> { };
            if (OneFilmSelected())
            {
                screeningList = GetSelectedFilm().FilmScreenings;
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
            _combineTitlesButton.Enabled = MultipleFilmsSelected() && !TextBeingEdited;
            _uncombineTitleButton.Enabled = OneFilmSelected() && !TextBeingEdited;
            _goToScreeningButton.Enabled = OneFilmSelected() && !TextBeingEdited;
            DoneButton.Enabled = !TextBeingEdited;
            DoneButton.Title = _titleByChanged[FilmRating.RatingChanged];
            WebLinkButton.Enabled = OneFilmSelected() && !TextBeingEdited;
            WebLinkButton.ToolTip = OneFilmSelected() ? ControlsFactory.VisitWebsiteButtonToolTip(CurrentFilm) : string.Empty;
        }

        public void SelectFilms(List<Film> films)
        {
            NSMutableIndexSet indices = new NSMutableIndexSet();
            foreach (var film in films)
            {
                int index = _filmTableDataSource.Films.IndexOf(film);
                if (index >= 0)
                {
                    indices.Add(new NSIndexSet(index));
                }
            }
            _filmRatingTableView.SelectRows(indices, false);
            if (indices.Count() > 0)
            {
                _filmRatingTableView.ScrollRowToVisible((nint)indices.First());
            }
        }

        public void SelectFilm(Film film)
        {
            SelectFilms(new List<Film> { film });
        }

        public List<Film> GetSelectedFilms()
        {
            var indexSet = FilmRatingTableView.SelectedRows;
            var rows = indexSet.ToArray();
            var selectedFilms = rows.Select(r => GetFilmByIndex(r)).ToList();
            return selectedFilms;
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

        public void ToggleOnlyFilmsWithScreenings()
        {
            // Toggle whether only films with screenings are displayd.
            OnlyFilmsWithScreenings = !OnlyFilmsWithScreenings;

            // Store the current selection of films.
            var selectedFilms = GetSelectedFilms();

            // Update the checkbox state.
            SetOnlyFilmsWithScreeningsStates();

            // Filter the data.
            SetFilmsWithScreenings();

            // Resort the data.
            if (!OnlyFilmsWithScreenings)
            {
                _filmTableDataSource.Sort(_filmTableDataSource.SortedBy,
                                          _filmTableDataSource.SortedAscending);
            }

            // Update the data source.
            _filmRatingTableView.ReloadData();

            // Update the button states.
            SetFilmRatingDialogButtonStates();

            // Try to select the stored films.
            SelectFilms(selectedFilms);
        }

        public void ToggleSubsectionFilter(Subsection subsection)
        {
            // Toggle between not filtered and filtered by the given subsection.
            FilteredSubsection = FilteredSubsection == null ? subsection : null;

            // Store the current selection of films.
            var selectedFilms = GetSelectedFilms();

            // Filter the data.
            FilterSubSection();

            // Resort the data.
            if (FilteredSubsection == null)
            {
                _filmTableDataSource.Sort(_filmTableDataSource.SortedBy,
                                          _filmTableDataSource.SortedAscending);
            }

            // Update the data source.
            _filmRatingTableView.ReloadData();

            // Try to select the stored films.
            SelectFilms(selectedFilms);
        }

        public void CloseDialog()
        {
            if (FilmRating.RatingChanged)
            {
                // Save the ratings.
                App.WriteFilmFanFilmRatings();
                FilmRating.RatingChanged = false;

                // Trigger a local notification.
                string title = "Ratings saved";
                string text = $"Film fan ratings have been saved in {AppDelegate.DocumentsFolder}.";
                AlertRaiser.RaiseNotification(title, text);
            }

            // Close the dialog.
            _presentor.DismissViewController(this);
        }
        #endregion

        #region Custom Actions
        partial void AcceptDialog(Foundation.NSObject sender)
        {
            CloseDialog();
        }

        [Action("ToggleOnlyFilmsWithScreenings:")]
        void ToggleOnlyFilmsWithScreenings(NSObject sender)
        {
            ToggleOnlyFilmsWithScreenings();
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

        [Action("ShowFilmInfo:")]
        void ShowScreenings(NSObject sender)
        {
            PerformSegue("GoToScreeningSegue", sender);
        }

        [Action("VisitFilmWebsite:")]
        public void VisitFilmWebsite(NSObject sender)
        {
            ViewController.VisitFilmWebsite(GetSelectedFilm());
        }
        #endregion
    }
}
