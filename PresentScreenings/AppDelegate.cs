using AppKit;
using Foundation;
using System;
using System.IO;
using ObjCRuntime;
using System.Linq;

namespace PresentScreenings.TableView
{
	/// <summary>
    /// App delegate, responsible for the life-cycle of the application by
    /// overriding functions called by the OS and for handling of other
    /// application level events.
	/// </summary>

    [Register("AppDelegate")]
	public partial class AppDelegate : NSApplicationDelegate
	{
        #region Static Properties
        public static string Festival { get; private set; }
        public static string FestivalYear { get; private set; }
        public static bool VisitPhysical { get; private set; }
        public static string DocumentsFolder => GetDocumentsPath();
        public static string AvailabilitiesFile { get; private set; }
        public static string ScreensFile { get; private set; }
        public static string FilmsFile { get; private set; }
        public static string ScreeningInfoFile { get; private set; }
        public static string ScreeningsFile { get; private set; }
        public static string RatingsFile {get; private set; }
        public static string FilmInfoFile {get; private set; }
        public static string RatingsSheetFile { get; private set; }
        public static string ScreeningsSummaryFile { get; private set; }
        public static TimeSpan PauseBetweenOnDemandScreenings { get; private set; }
        public static TimeSpan DaySpan => new TimeSpan(24, 0, 0);
        #endregion

        #region Properties
        public ViewController Controller { get; set; } = null;
        public AnalyserDialogController AnalyserDialogController { get; set; }
        public AvailabilityDialogControler AvailabilityDialogControler { get; set; }
        public CombineTitlesSheetController CombineTitleController { get; set; }
        public FilmInfoDialogController FilmInfoController { get; set; }
        public FilmRatingDialogController FilmsDialogController { get; set; }
        public PlannerDialogController PlannerDialogController { get; set; }
        public UncombineTitlesSheetController UncombineTitleController { get; set; }
        public ScreeningMenuDelegate ScreeningMenuDelegate => (ScreeningMenuDelegate)_screeningMenu.Delegate;
        public NSMenuItem ToggleTypeMatchMenuItem => _toggleTypeMatchMethod;
        #endregion

        #region Constructors
        public AppDelegate()
		{
            // Preferences.
            Festival = "IFFR";
            FestivalYear = "2021";
            VisitPhysical = false;
            PauseBetweenOnDemandScreenings = new TimeSpan(0, 30, 0);
            Screening.TravelTime = new TimeSpan(0, 30, 0);
            FilmRatingDialogController.OnlyFilmsWithScreenings = false;
            FilmRatingDialogController.MinimalDuration = new TimeSpan(0, 35, 0);
            ScreeningControl.UseCoreGraphics = false;

            // Make sure the documents directory exists.
            _ = Directory.CreateDirectory(DocumentsFolder);

            // Set load/unload file names.
            AvailabilitiesFile = Path.Combine(DocumentsFolder, "availabilities.csv");
            ScreensFile = Path.Combine(DocumentsFolder, "screens.csv");
            FilmsFile = Path.Combine(DocumentsFolder, "films.csv");
            ScreeningInfoFile = Path.Combine(DocumentsFolder, "screeninginfo.csv");
            ScreeningsFile = Path.Combine(DocumentsFolder, "screenings.csv");
            RatingsFile = Path.Combine(DocumentsFolder, "ratings.csv");
            FilmInfoFile = Path.Combine(DocumentsFolder, "filminfo.xml");
            RatingsSheetFile = Path.Combine(DocumentsFolder, "RatingsSheet.csv");
            ScreeningsSummaryFile = Path.Combine(DocumentsFolder, "Screenings Summary.csv");
        }
        #endregion

        #region Override Methods
        public override void DidFinishLaunching(NSNotification notification)
        {
            // Insert code here to initialize your application.
			_navigateMenu.AutoEnablesItems = false;
            _navigateMenu.Delegate = new NavigateMenuDelegate(_navigateMenu, Controller);
            _screeningMenu.AutoEnablesItems = false;
            _screeningMenu.Delegate = new ScreeningMenuDelegate(this, _screeningMenu);
            _filmsMenu.AutoEnablesItems = false;
            _filmsMenu.Delegate = new FilmsMenuDelegate(this, _filmsMenu);
            _programMenu.AutoEnablesItems = false;
            _programMenu.Delegate = new ProgramMenuDelegate(this, _programMenu);
            ToggleTypeMatchMenuItem.Action = new Selector("ToggleTypeMatchMethod:");
            _showScreeningsMenuItem.Action = new Selector("ShowFilmInfo:");
            _combineTitlesMenuItem.Action = new Selector("SelectTitlesToCombine:");
            _uncombineTitleMenuItem.Action = new Selector("ShowTitlesToUncombine:");
            Controller.ClickableLabelsMenuItem = _clickableLabelsMenuItem;

            //// Report coinciding screenings.
            //ViewController.ReportDuplicateScreenings();
            //ViewController.ReportCoincidingScreeninings();
        }

        public override void WillTerminate(NSNotification notification)
		{
			// Insert code here to tear down your application
		}

		public override bool ApplicationShouldTerminateAfterLastWindowClosed(NSApplication sender)
		{
			return true;
		}
        #endregion

        #region Private Methods
        private static string GetDocumentsPath()
        {
            string homeFolder = Environment.GetFolderPath(Environment.SpecialFolder.Personal);
            return homeFolder + $"/Documents/Film/{Festival}/{Festival}{FestivalYear}/FestivalPlan";
        }

        private void ShowSaveAs()
        {
            var dlg = new NSSavePanel
            {
                Title = "Save Screenings Plan",
                Message = "Please save your screens",
                NameFieldLabel = "Save screens as",
                AllowedFileTypes = new string[] { "csv" },
                ExtensionHidden = false,
                CanCreateDirectories = true,
                ShowsTagField = false
            };

            dlg.BeginSheet(Controller.TableView.Window, (result) =>
            {
                string directory = dlg.Directory;

                // Write film fan availability.
                WriteFilmFanAvailabilities(directory);

                // Write film ratings.
                WriteFilmFanFilmRatings(directory);

                // Write screening info.
                string screeningInfoFileName = Path.GetFileName(ScreeningInfoFile);
                string screeningInfosPath = Path.Combine(directory, screeningInfoFileName);
                new ScreeningInfo().WriteListToFile(screeningInfosPath, ScreeningsPlan.ScreeningInfos);
            });
        }
        public void WriteFilmFanAvailabilities(string directory = null)
        {
            if (directory == null)
            {
                directory = DocumentsFolder;
            }
            string availabilitiesFileName = Path.GetFileName(AvailabilitiesFile);
            string availabilitiesPath = Path.Combine(directory, availabilitiesFileName);
            new FilmFanAvailability().WriteListToFile(availabilitiesPath, ScreeningsPlan.Availabilities);
        }

        public void WriteFilmFanFilmRatings(string directory = null)
        {
            if (directory == null)
            {
                directory = DocumentsFolder;
            }

            // Save the ratings.
            string ratingsFileName = Path.GetFileName(RatingsFile);
            string ratingsPath = Path.Combine(directory, ratingsFileName);
            new FilmFanFilmRating().WriteListToFile(ratingsPath, ScreeningsPlan.FilmFanFilmRatings);

            // Write ratings sheet.
            string sheetFileName = Path.GetFileName(RatingsSheetFile);
            string sheetPath = Path.Combine(directory, sheetFileName);
            new Film().WriteListToFile(sheetPath, ScreeningsPlan.Films.Where(f =>
            {
                return f.Duration >= FilmRatingDialogController.MinimalDuration;
            }).ToList());

            // Write screenings summary.
            string summaryFileName = Path.GetFileName(ScreeningsSummaryFile);
            string summaryPath = Path.Combine(directory, summaryFileName);
            new Screening().WriteListToFile(summaryPath, Controller.Plan.AttendedScreenings());
        }
        #endregion

        #region Custom Actions
        partial void ToggleClickableLabels(Foundation.NSObject sender)
        {
            Controller.ToggleClickableLabels();
        }

        partial void ShowScreeningInfo(Foundation.NSObject sender)
        {
            Controller.ShowScreeningInfo();
        }

        [Action("ShowFilmInfo:")]
        internal void ShowFilmInfo(NSObject sender)
        {
            Controller.ShowFilmInfo(sender);
        }

        [Action("VisitFilmWebsite:")]
        internal void VisitFilmWebsite(NSObject sender)
        {
            ViewController.VisitFilmWebsite(Controller.CurrentFilm);
        }

        partial void ToggleTicketsBought(Foundation.NSObject sender)
        {
            Controller.ToggleTicketsBought();
        }

        partial void ToggleSoldOut(Foundation.NSObject sender)
        {
            Controller.ToggleSoldOut();
        }

		partial void navigatePreviousDay(NSObject sender)
		{
			Controller.SetNextDay(-1);
		}

		partial void navigateNextDay(NSObject sender)
		{
			Controller.SetNextDay(1);
		}

        partial void navigatePreviousScreen(Foundation.NSObject sender)
        {
            Controller.SetNextScreen(-1);
        }

        partial void navigateNextScreen(Foundation.NSObject sender)
        {
            Controller.SetNextScreen(1);
        }

        partial void navigateNextScreening (Foundation.NSObject sender)
        {
            Controller.SetNextScreening();
        }

        partial void navigatePreviousScreening (Foundation.NSObject sender)
        {
            Controller.SetPreviousScreening();
        }

        internal void NavigateFilmScreening(Screening screening)
        {
            if (FilmsDialogController != null)
            {
                FilmsDialogController.CloseDialog();
            }
            if (FilmInfoController != null)
            {
                FilmInfoController.CloseDialog();
            }
            if (AnalyserDialogController != null)
            {
                AnalyserDialogController.CloseDialog();
            }
            Controller.GoToScreening(screening);
        }

        [Action("NavigateFilmScreening:")]
        internal void NavigateFilmScreening(NSObject sender)
        {
            var screening = ScreeningMenuDelegate.FilmScreening(((NSMenuItem)sender).Title);
            NavigateFilmScreening(screening);
        }

        [Action("ToggleAttendance:")]
        internal void ToggleAttendance(NSObject sender)
        {
            string filmFan = ((NSMenuItem)sender).Title;
            Controller.ToggleAttendance(filmFan);
        }

        [Action("MoveBackward:")]
        internal void MoveBackward(NSObject sender)
        {
            Controller.MoveScreening(false);
        }

        [Action("MoveForward:")]
        internal void MoveForward(NSObject sender)
        {
            Controller.MoveScreening(true);
        }

        [Action("MoveToPreviousDay:")]
        internal void MoveToPreviousDay(NSObject sender)
        {
            Controller.MoveScreening24Hours(false);
        }

        [Action("MoveToNextDay:")]
        internal void MoveToNextDay(NSObject sender)
        {
            Controller.MoveScreening24Hours(true);
        }

        [Export("saveDocumentAs:")]
        void ShowSaveAs(NSObject sender)
        {
            ShowSaveAs();
        }
        #endregion
    }
}
