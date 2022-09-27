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
	[Register ("MainWindowController")]
	partial class MainWindowController
	{
		[Outlet]
		Foundation.NSObject _alerToolbarItem { get; set; }

		[Outlet]
		Foundation.NSObject _nextDayToolbarItem { get; set; }

		[Outlet]
		Foundation.NSObject _previousDayToolbarItem { get; set; }

		[Outlet]
		AppKit.NSToolbarItem _saveToolbarItem { get; set; }

		[Outlet]
		AppKit.NSToolbarItem _showFilmInfoToolbarItem { get; set; }

		[Outlet]
		AppKit.NSToolbarItem _showRatingsToolbarItem { get; set; }

		[Outlet]
		AppKit.NSToolbarItem _showScreeningInfoToolbarItem { get; set; }

		[Outlet]
		PresentScreenings.TableView.ActivatableToolbarItem _ticketAlertsToolbarItem { get; set; }

		[Outlet]
		AppKit.NSToolbarItem _vistWebsiteToolbarItem { get; set; }

		[Action ("ShowFilmInfo:")]
		partial void ShowFilmInfo (Foundation.NSObject sender);

		[Action ("ShowFilmRatings:")]
		partial void ShowFilmRatings (Foundation.NSObject sender);

		[Action ("ShowScreeningInfo:")]
		partial void ShowScreeningInfo (Foundation.NSObject sender);

		[Action ("VisitWebSite:")]
		partial void VisitWebSite (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (_alerToolbarItem != null) {
				_alerToolbarItem.Dispose ();
				_alerToolbarItem = null;
			}

			if (_nextDayToolbarItem != null) {
				_nextDayToolbarItem.Dispose ();
				_nextDayToolbarItem = null;
			}

			if (_previousDayToolbarItem != null) {
				_previousDayToolbarItem.Dispose ();
				_previousDayToolbarItem = null;
			}

			if (_saveToolbarItem != null) {
				_saveToolbarItem.Dispose ();
				_saveToolbarItem = null;
			}

			if (_ticketAlertsToolbarItem != null) {
				_ticketAlertsToolbarItem.Dispose ();
				_ticketAlertsToolbarItem = null;
			}

			if (_vistWebsiteToolbarItem != null) {
				_vistWebsiteToolbarItem.Dispose ();
				_vistWebsiteToolbarItem = null;
			}

			if (_showFilmInfoToolbarItem != null) {
				_showFilmInfoToolbarItem.Dispose ();
				_showFilmInfoToolbarItem = null;
			}

			if (_showScreeningInfoToolbarItem != null) {
				_showScreeningInfoToolbarItem.Dispose ();
				_showScreeningInfoToolbarItem = null;
			}

			if (_showRatingsToolbarItem != null) {
				_showRatingsToolbarItem.Dispose ();
				_showRatingsToolbarItem = null;
			}
		}
	}
}
