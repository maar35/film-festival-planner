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
        #endregion

        #region Properties
        public ViewController Controller { get; set; } = null;
        public FilmRatingDialogController FilmsDialogController { get; set; }
        public AnalyserDialogController AnalyserDialogController { get; set; }
        public CombineTitlesSheetController CombineTitleController { get; set; }
        public UncombineTitlesSheetController UncombineTitleController;
        public FilmInfoDialogController filmInfoController;
        public DownloadFilmInfoController DownloadFilmInfoController;
        public PlannerDialogController PlannerDialogController;
        public ScreeningMenuDelegate ScreeningMenuDelegate => (ScreeningMenuDelegate)_screeningMenu.Delegate;
        public NSMenuItem ToggleTypeMatchMenuItem => _toggleTypeMatchMethod;
        #endregion

        #region Constructors
        public AppDelegate()
		{
            // Preferences.
            Festival = "NFF";
            FestivalYear = "2020";
            Screening.TravelTime = new TimeSpan(0, 30, 0);
            FilmRatingDialogController.OnlyFilmsWithScreenings = true;
            FilmRatingDialogController.MinimalDuration = new TimeSpan(0, 35, 0);
            ScreeningControl.UseCoreGraphics = false;
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
            _filmsMenu.Delegate = new FilmsMenuDelegate(this);
            _programMenu.AutoEnablesItems = false;
            _programMenu.Delegate = new ProgramMenuDelegate(this, _programMenu);
            ToggleTypeMatchMenuItem.Action = new Selector("ToggleTypeMatchMethod:");
            _showScreeningsMenuItem.Action = new Selector("ShowScreenings:");
            _combineTitlesMenuItem.Action = new Selector("SelectTitlesToCombine:");
            _uncombineTitleMenuItem.Action = new Selector("ShowTitlesToUncombine:");
            Controller.ClickableLabelsMenuItem = _clickableLabelsMenuItem;
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

        #region Custom Actions
        [Export("saveDocumentAs:")]
        void ShowSaveAs(NSObject sender)
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

                // Write film info.
                FilmInfo.SaveFilmInfoAsXml(ScreeningsPlan.FilmInfos, Path.Combine(directory, "filminfo.xml"));

                // Write film ratings.
                string ratingsPath = Path.Combine(directory, "ratings.csv");
                new FilmFanFilmRating().WriteListToFile(ratingsPath, ScreeningsPlan.FilmFanFilmRatings);

                // Write screening info.
                string screeningInfosPath = Path.Combine(directory, "screeninginfo.csv");
                new ScreeningInfo().WriteListToFile(screeningInfosPath, ScreeningsPlan.ScreeningInfos);

                // Write screenings summary.
                string summaryPath = Path.Combine(directory, "Screenings Summary.csv");
                new Screening().WriteListToFile(summaryPath, Controller.Plan.AttendedScreenings());

                // Write ratings sheet.
                string sheetPath = Path.Combine(directory, "RatingsSheet.csv");
                new Film().WriteListToFile(sheetPath, ScreeningsPlan.Films.Where(f => f.Duration >= FilmRatingDialogController.MinimalDuration).ToList());
            });

        }

        partial void ToggleClickableLabels(Foundation.NSObject sender)
        {
            Controller.ToggleClickableLabels();
        }

        partial void ShowScreeningInfo(Foundation.NSObject sender)
        {
            Controller.ShowScreeningInfo();
        }

        partial void ShowFilmRatings(Foundation.NSObject sender)
        {
            Controller.PerformSegue("FilmRatingSegue", sender);
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

        [Action("NavigateFilmScreening:")]
        internal void NavigateFilmScreening(NSObject sender)
        {
            if (FilmsDialogController != null)
            {
                FilmsDialogController.CloseDialog();
            }
            if (AnalyserDialogController != null)
            {
                AnalyserDialogController.CloseDialog();
            }
            var screening = ScreeningMenuDelegate.FilmScreening(((NSMenuItem)sender).Title);
            Controller.GoToScreening(screening);
        }

        [Action("ToggleAttendance:")]
        internal void ToggleAttendance(NSObject sender)
        {
            string filmFan = ((NSMenuItem)sender).Title;
            Controller.ToggleAttendance(filmFan);
        }
        #endregion
    }
}
