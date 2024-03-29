﻿using AppKit;
using Foundation;
using System;
using System.IO;
using ObjCRuntime;
using System.Linq;
using YamlDotNet.Serialization.NamingConventions;
using System.Threading.Tasks;

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
        public static Configuration Config { get; private set; }
        public static string Festival { get; private set; }
        public static string FestivalYear { get; private set; }
        public static bool VisitPhysical { get; private set; }
        public static string HomePath => GetHomePath();
        public static string CommonDataFolder => GetCommonDataPath();
        public static string DocumentsFolder => GetDocumentsPath();
        public static string WebColorsFolder => GetWebColorsPath();
        public static string ConfigFile => GetConfigFilePath();
        public static string AvailabilitiesFile { get; private set; }
        public static string CitiesFile { get; private set; }
        public static string TheatersFile { get; private set; }
        public static string ScreensFile { get; private set; }
        public static string FilmsFile { get; private set; }
        public static string SectionsFile { get; private set; }
        public static string SubsectionsFile { get; private set; }
        public static string ScreeningInfoFile { get; private set; }
        public static string ScreeningsFile { get; private set; }
        public static string RatingsFile {get; private set; }
        public static string FilmInfoFile {get; private set; }
        public static string RatingsSheetFile { get; private set; }
        public static string ScreeningsSummaryFile { get; private set; }
        public static string WebColorsFile { get; private set; }
        public static int MaxShortMinutes { get; private set; }
        public static TimeSpan PauseBetweenOnDemandScreenings { get; private set; }
        public static TimeSpan DaySpan => new TimeSpan(24, 0, 0);
        public static TimeSpan MaxShortDuration { get; private set; }
        #endregion

        #region Properties
        public MainWindowController MainWindowController { get; set; }
        public ViewController Controller { get; set; } = null;
        public AnalyserDialogController AnalyserDialogController { get; set; }
        public AvailabilityDialogControler AvailabilityDialogControler { get; set; }
        public CombineTitlesSheetController CombineTitleController { get; set; }
        public FilmInfoDialogController FilmInfoController { get; set; }
        public FilmRatingDialogController FilmsDialogController { get; set; }
        public PlannerDialogController PlannerDialogController { get; set; }
        public UncombineTitlesSheetController UncombineTitleController { get; set; }
        public WarningsDialogControler WarningsController { get; set; }
        public ScreeningMenuDelegate ScreeningMenuDelegate => (ScreeningMenuDelegate)_screeningMenu.Delegate;
        public NSMenuItem ToggleOnlyFilmsWithScreeningsMenuItem => _filmsMenu.ItemWithTag(FilmsMenuDelegate.ToggleOnlyFilmsWithScreeningsMenuItemTag);
        public NSMenuItem ToggleTypeMatchMenuItem => _filmsMenu.ItemWithTag(FilmsMenuDelegate.ToggleTypeMatchMethodMenuItemTag);
        public NSMenuItem ReloadRatingsMenuItemTag => _filmsMenu.ItemWithTag(FilmsMenuDelegate.ReloadRatingsMenuItemTag);
        #endregion

        #region Constructors
        public AppDelegate()
		{
            // Load the configuration.
            Config = GetConfiguration();

            // Preferences.
            Festival = "MTMF";
            FestivalYear = "2024";
            VisitPhysical = true;

            MaxShortMinutes = int.Parse(Config.Constants["MaxShortMinutes"]);
            MaxShortDuration = new TimeSpan(0, MaxShortMinutes, 0);
            PauseBetweenOnDemandScreenings = new TimeSpan(0, 30, 0);
            Screening.WalkTimeSameTheater = new TimeSpan(0, 15, 0);
            Screening.TravelTimeOtherTheater = new TimeSpan(0, 40, 0);
            FilmRatingDialogController.OnlyFilmsWithScreenings = false;
            DaySchemaScreeningControl.UseCoreGraphics = false;

            // Make sure the documents directories exist.
            _ = Directory.CreateDirectory(DocumentsFolder);
            _ = Directory.CreateDirectory(CommonDataFolder);

            // Set load/unload file names.
            AvailabilitiesFile = Path.Combine(DocumentsFolder, "availabilities.csv");
            CitiesFile = Path.Combine(CommonDataFolder, "cities.csv");
            TheatersFile = Path.Combine(CommonDataFolder, "theaters.csv");
            ScreensFile = Path.Combine(CommonDataFolder, "screens.csv");
            FilmsFile = Path.Combine(DocumentsFolder, "films.csv");
            SectionsFile = Path.Combine(DocumentsFolder, "sections.csv");
            SubsectionsFile = Path.Combine(DocumentsFolder, "subsections.csv");
            ScreeningInfoFile = Path.Combine(DocumentsFolder, "screeninginfo.csv");
            ScreeningsFile = Path.Combine(DocumentsFolder, "screenings.csv");
            RatingsFile = Path.Combine(DocumentsFolder, "ratings.csv");
            FilmInfoFile = Path.Combine(DocumentsFolder, "filminfo.xml");
            RatingsSheetFile = Path.Combine(DocumentsFolder, "RatingsSheet.csv");
            ScreeningsSummaryFile = Path.Combine(DocumentsFolder, "Screenings Summary.csv");
            WebColorsFile = Path.Combine(WebColorsFolder, "webcolors.txt");
        }
        #endregion

        #region Override Methods
        public override void DidFinishLaunching(NSNotification notification)
        {
            // Initialize menu delegates.
            _navigateMenu.AutoEnablesItems = false;
            _navigateMenu.Delegate = new NavigateMenuDelegate(Controller);
            _screeningMenu.AutoEnablesItems = false;
            _screeningMenu.Delegate = new ScreeningMenuDelegate(this, _screeningMenu);
            _filmsMenu.AutoEnablesItems = false;
            _filmsMenu.Delegate = new FilmsMenuDelegate(this);
            _programMenu.AutoEnablesItems = false;
            _programMenu.Delegate = new ProgramMenuDelegate(Controller);

            // Set actions of menu items.
            _showScreeningsMenuItem.Action = new Selector("ShowFilmInfo:");
            _combineTitlesMenuItem.Action = new Selector("SelectTitlesToCombine:");
            _uncombineTitleMenuItem.Action = new Selector("ShowTitlesToUncombine:");
            ReloadRatingsMenuItemTag.Action = new Selector("ReloadRatings:");
            ToggleOnlyFilmsWithScreeningsMenuItem.Action = new Selector("ToggleOnlyFilmsWithScreenings:");
            ToggleTypeMatchMenuItem.Action = new Selector("ToggleTypeMatchMethod:");

            // Pass outlets to the View Controller.
            Controller.ClickableLabelsMenuItem = _clickableLabelsMenuItem;

            // Report coinciding screenings.
            ViewController.ReportDuplicateScreenings();
            ViewController.ReportCoincidingScreeninings();
        }

        public override void WillTerminate(NSNotification notification)
		{
			// Insert code here to tear down your application
		}

        public override NSApplicationTerminateReply ApplicationShouldTerminate(NSApplication sender)
        {
            // See if any window needs to be saved first
            foreach (NSWindow window in NSApplication.SharedApplication.Windows)
            {
                if (window.Delegate != null && !window.Delegate.WindowShouldClose(this))
                {
                    // Did the window terminate the close?
                    return NSApplicationTerminateReply.Cancel;
                }
            }

            // Allow normal termination.
            return NSApplicationTerminateReply.Now;
        }

        public override bool ApplicationShouldTerminateAfterLastWindowClosed(NSApplication sender)
		{
			return true;
		}
        #endregion

        #region Public Methods
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

        public void WriteRatingsSheet(string directory = null)
        {
            if (directory == null)
            {
                directory = DocumentsFolder;
            }
            string sheetFileName = Path.GetFileName(RatingsSheetFile);
            string sheetPath = Path.Combine(directory, sheetFileName);
            new Film().WriteListToFile(sheetPath, ScreeningsPlan.Films.Where(f =>
            {
                return f.Duration > MaxShortDuration;
            }).ToList());
        }

        public void WriteScreeningInfo(string directory = null)
        {
            if (directory == null)
            {
                directory = DocumentsFolder;
            }

            // Save the screening info.
            string screeningInfoFileName = Path.GetFileName(ScreeningInfoFile);
            string screeningInfosPath = Path.Combine(directory, screeningInfoFileName);
            new ScreeningInfo().WriteListToFile(screeningInfosPath, ScreeningsPlan.ScreeningInfos);

            // Write screenings summary.
            WriteScreeningsSummary(directory);
        }

        public void RunSaveDialog()
        {
            // Create the Save alert.
            string alertTitle = "Save Festival Data";
            string okButtonTitle = "OK";
            string informativeText = $"Please hit the {okButtonTitle} button to save the {Festival}{FestivalYear} data";
            var alert = new NSAlert()
            {
                AlertStyle = NSAlertStyle.Informational,
                MessageText = alertTitle,
                InformativeText = informativeText,
            };
            alert.AddButton(okButtonTitle);
            alert.AddButton("Cancel");

            // Run the alert.
            var alertResult = alert.RunModal();

            // Take action based on the button pressed.
            if (alertResult == 1000)
            {
                SaveFestivalData();
            }
        }
        #endregion

        #region Private Methods
        private static string GetHomePath()
        {
            return Environment.GetFolderPath(Environment.SpecialFolder.Personal);
        }

        private static string GetConfigFilePath()
        {
            return $"{HomePath}/Projects/FilmFestivalPlanner/Configs/common.yml";
        }

        private static string GetCommonDataPath()
        {
            var commonDataPath = Config.Paths["CommonDataDirectory"];
            return $"{HomePath}/{commonDataPath}";
        }

        private static string GetDocumentsPath()
        {
            var festivalRoot = Config.Paths["FestivalRootDirectory"];
            return $"{HomePath}/{festivalRoot}/{Festival}/{Festival}{FestivalYear}/FestivalPlan";
        }

        private static string GetWebColorsPath()
        {
            return $"{HomePath}/Projects/FilmFestivalPlanner";
        }

        private Configuration GetConfiguration()
        {
            var deserializer = new YamlDotNet.Serialization.DeserializerBuilder()
                .WithNamingConvention(PascalCaseNamingConvention.Instance)
                .Build();
            var yamlText = File.ReadAllText(GetConfigFilePath());
            return deserializer.Deserialize<Configuration>(yamlText);
        }

        private void SaveFestivalData()
        {
            // Write film fan availability.
            WriteFilmFanAvailabilities(DocumentsFolder);

            // Write the ratings sheet.
            WriteRatingsSheet(DocumentsFolder);

            // Write screening info.
            WriteScreeningInfo(DocumentsFolder);

            // Display where the files have been stored.
            string title = "Festival Data Saved";
            string text = $"Files of {Festival}{FestivalYear} are saved in {DocumentsFolder}";
            AlertRaiser.RaiseNotification(title, text);

            // Unset the dirty window indicator.
            Controller.View.Window.DocumentEdited = false;
        }

        private void WriteScreeningsSummary(string directory)
        {
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

        [Action("ReloadRatings:")]
        internal void ReloadRatings(NSObject sender)
        {
            Controller.ReloadRatings();
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

        internal async void NavigateFilmScreening(Screening screening)
        {
            // Close the film info dialog when running.
            if (FilmInfoController != null)
            {
                FilmInfoController.CloseDialog();
            }

            // Prevents the app from freezing when the last dialog is closed.
            await Task.Delay(100);

            // Close the film ratings dialog when running.
            if (FilmsDialogController != null)
            {
                FilmsDialogController.CloseDialog();
            }

            // Close the analyser dialog when running.
            if (AnalyserDialogController != null)
            {
                AnalyserDialogController.CloseDialog();
            }

            // Open the screening info dialog of the given screening.
            Controller.GoToScreening(screening);
        }

        [Action("NavigateFilmScreening:")]
        internal void NavigateFilmScreening(NSObject sender)
        {
            var screening = ScreeningMenuDelegate.FilmScreening(((NSMenuItem)sender).Title);
            NavigateFilmScreening(screening);
        }

        internal void NavigateToFilm(int filmId)
        {
            if (FilmInfoController != null)
            {
                FilmInfoController.CloseDialog();
            }
            Film film = ViewController.GetFilmById(filmId);
            FilmsDialogController.SelectFilm(film);
        }

        [Action("NavigateToFilm:")]
        internal void NavigateToFilm(NSObject sender)
        {
            int filmId = int.Parse(((NSMenuItem)sender).Identifier);
            NavigateToFilm(filmId);
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
            Controller.MoveScreeningOvernight(false);
        }

        [Action("MoveToNextDay:")]
        internal void MoveToNextDay(NSObject sender)
        {
            Controller.MoveScreeningOvernight(true);
        }

        [Export("saveDocument:")]
        void ShowSave(NSObject sender)
        {
            RunSaveDialog();
        }
        #endregion
    }
}
