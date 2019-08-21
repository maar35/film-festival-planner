using AppKit;
using Foundation;
using System;
using System.IO;
using ObjCRuntime;

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
        #region Private Members
        #endregion

        #region Properties
        public ViewController Controller { get; set; } = null;
        public FilmRatingDialogController FilmsDialogController { get; set; }
        public CombineTitlesSheetController CombineTitleController { get; set; }
        public UncombineTitlesSheetController UncombineTitleController;
        public FilmInfoDialogController filmInfoController;
        public DownloadFilmInfoController DownloadFilmInfoController;
        public ScreeningMenuDelegate ScreeningMenuDelegate => (ScreeningMenuDelegate)_screeningMenu.Delegate;
        public NSMenuItem ToggleTypeMatchMenuItem { get => _toggleTypeMatchMethod; }
		#endregion

		#region Constructors
		public AppDelegate()
		{
		}
		#endregion

		#region Override Methods
		public override void DidFinishLaunching(NSNotification notification)
		{
            // Insert code here to initialize your application
			_navigateMenu.AutoEnablesItems = false;
            _navigateMenu.Delegate = new NavigateMenuDelegate(_navigateMenu, Controller);
            _screeningMenu.AutoEnablesItems = false;
            _screeningMenu.Delegate = new ScreeningMenuDelegate(this, _myAttendanceMenuItem);
            _filmsMenu.AutoEnablesItems = false;
            _filmsMenu.Delegate = new FilmsMenuDelegate(this);
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

                // Write screens.
                string screensPath = Path.Combine(directory, "screens.csv");
                new ListWriter<Screen>(screensPath).WriteListToFile(ScreeningsPlan.Screens);

                // Write films.
                string filmsPath = Path.Combine(directory, "films.csv");
                new ListWriter<Film>(filmsPath, Film.WriteHeader).WriteListToFile(ScreeningsPlan.Films);

                // Write film info.
                FilmInfo.SaveFilmInfoAsXml(ScreeningsPlan.FilmInfos, Path.Combine(directory, "filminfo.xml"));

                // Write film ratings.
                string filmFanRatingsPath = Path.Combine(directory, "filmfanfilmratings.csv");
                new ListWriter<FilmFanFilmRating>(filmFanRatingsPath, FilmFanFilmRating.WriteHeader).WriteListToFile(ScreeningsPlan.FilmFanFilmRatings);

                // Write screenings.
                string screeningsPath = Path.Combine(directory, "screenings.csv");
                new ListWriter<Screening>(screeningsPath, Screening.WriteHeader).WriteListToFile(ScreeningsPlan.Screenings);

                // Write screening info.
                string screeningInfosPath = Path.Combine(directory, "screeninginfo.csv");
                new ListWriter<ScreeningInfo>(screeningInfosPath, ScreeningInfo.WriteHeader).WriteListToFile(ScreeningsPlan.ScreeningInfos);

                // Write screenings overview.
                string overviewPath = Path.Combine(directory, "Screenings Summary.csv");
                var overviewWriter = new ListWriter<Screening>(overviewPath, Screening.WriteOverviewHeader);
                overviewWriter.WriteListToFile(Controller.Plan.AttendedScreenings(), Screening.WriteOverviewRecord);
            });
        }

        partial void ToggleClickableLabels(Foundation.NSObject sender)
        {
            Controller.ToggleClickableLabels();
        }

        partial void DownloadFilmInfo(NSObject sender)
        {
            Controller.DownloadFilmInfo(sender);
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

        partial void ToggleMyAttandance(Foundation.NSObject sender)
        {
            Controller.ToggleMyAttendance();
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
            if(FilmsDialogController != null)
            {
                FilmsDialogController.CloseDialog();
            }
            var screening = ScreeningMenuDelegate.FilmScreening(((NSMenuItem)sender).Title);
            Controller.GoToScreening(screening);
        }

        [Action("ToggleFriendAttendance:")]
        internal void ToggleFriendAttendance(NSObject sender)
        {
            string friend = ((NSMenuItem)sender).Title;
            Controller.ToggleFriendAttendance(friend);
        }
        #endregion
	}
}
