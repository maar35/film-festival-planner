// WARNING
//
// This file has been generated automatically by Visual Studio to store outlets and
// actions made in the UI designer. If it is removed, they will be lost.
// Manual changes to this file may not be handled correctly.
//
using Foundation;
using System.CodeDom.Compiler;

namespace PresentScreenings.TableView
{
	partial class AppDelegate
	{
		[Outlet]
		AppKit.NSMenuItem _clickableLabelsMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenuItem _combineTitlesMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenu _filmsMenu { get; set; }

		[Outlet]
		AppKit.NSMenu _navigateMenu { get; set; }

		[Outlet]
		AppKit.NSMenuItem _plannerMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenu _programMenu { get; set; }

		[Outlet]
		AppKit.NSMenu _screeningMenu { get; set; }

		[Outlet]
		AppKit.NSMenuItem _showFilmRatingsMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenuItem _showScreeningInfoMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenuItem _showScreeningsMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenuItem _soldOutMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenuItem _ticketsBoughtMenuItem { get; set; }

		[Outlet]
		AppKit.NSMenuItem _toggleTypeMatchMethod { get; set; }

		[Outlet]
		AppKit.NSMenuItem _uncombineTitleMenuItem { get; set; }

		[Action ("DownloadFilmInfo:")]
		partial void DownloadFilmInfo (Foundation.NSObject sender);

		[Action ("navigateNextDay:")]
		partial void navigateNextDay (Foundation.NSObject sender);

		[Action ("navigateNextScreen:")]
		partial void navigateNextScreen (Foundation.NSObject sender);

		[Action ("navigateNextScreening:")]
		partial void navigateNextScreening (Foundation.NSObject sender);

		[Action ("navigatePreviousDay:")]
		partial void navigatePreviousDay (Foundation.NSObject sender);

		[Action ("navigatePreviousScreen:")]
		partial void navigatePreviousScreen (Foundation.NSObject sender);

		[Action ("navigatePreviousScreening:")]
		partial void navigatePreviousScreening (Foundation.NSObject sender);

		[Action ("ShowFilmRatings:")]
		partial void ShowFilmRatings (Foundation.NSObject sender);

		[Action ("ShowScreeningInfo:")]
		partial void ShowScreeningInfo (Foundation.NSObject sender);

		[Action ("StartPlanner:")]
		partial void StartPlanner (Foundation.NSObject sender);

		[Action ("ToggleClickableLabels:")]
		partial void ToggleClickableLabels (Foundation.NSObject sender);

		[Action ("ToggleSoldOut:")]
		partial void ToggleSoldOut (Foundation.NSObject sender);

		[Action ("ToggleTicketsBought:")]
		partial void ToggleTicketsBought (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (_plannerMenuItem != null) {
				_plannerMenuItem.Dispose ();
				_plannerMenuItem = null;
			}

			if (_clickableLabelsMenuItem != null) {
				_clickableLabelsMenuItem.Dispose ();
				_clickableLabelsMenuItem = null;
			}

			if (_programMenu != null) {
				_programMenu.Dispose ();
				_programMenu = null;
			}

			if (_combineTitlesMenuItem != null) {
				_combineTitlesMenuItem.Dispose ();
				_combineTitlesMenuItem = null;
			}

			if (_filmsMenu != null) {
				_filmsMenu.Dispose ();
				_filmsMenu = null;
			}

			if (_navigateMenu != null) {
				_navigateMenu.Dispose ();
				_navigateMenu = null;
			}

			if (_screeningMenu != null) {
				_screeningMenu.Dispose ();
				_screeningMenu = null;
			}

			if (_showFilmRatingsMenuItem != null) {
				_showFilmRatingsMenuItem.Dispose ();
				_showFilmRatingsMenuItem = null;
			}

			if (_showScreeningInfoMenuItem != null) {
				_showScreeningInfoMenuItem.Dispose ();
				_showScreeningInfoMenuItem = null;
			}

			if (_showScreeningsMenuItem != null) {
				_showScreeningsMenuItem.Dispose ();
				_showScreeningsMenuItem = null;
			}

			if (_soldOutMenuItem != null) {
				_soldOutMenuItem.Dispose ();
				_soldOutMenuItem = null;
			}

			if (_ticketsBoughtMenuItem != null) {
				_ticketsBoughtMenuItem.Dispose ();
				_ticketsBoughtMenuItem = null;
			}

			if (_toggleTypeMatchMethod != null) {
				_toggleTypeMatchMethod.Dispose ();
				_toggleTypeMatchMethod = null;
			}

			if (_uncombineTitleMenuItem != null) {
				_uncombineTitleMenuItem.Dispose ();
				_uncombineTitleMenuItem = null;
			}
		}
	}
}
