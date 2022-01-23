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
	[Register ("FilmRatingDialogController")]
	partial class FilmRatingDialogController
	{
		[Outlet]
		AppKit.NSButton _closeButton { get; set; }

		[Outlet]
		AppKit.NSButton _combineTitlesButton { get; set; }

		[Outlet]
		AppKit.NSButton _downloadFilmInfoButton { get; set; }

		[Outlet]
		AppKit.NSTableView _filmRatingTableView { get; set; }

		[Outlet]
		AppKit.NSButton _goToScreeningButton { get; set; }

		[Outlet]
		AppKit.NSButton _onlyFilmsWithScreeningsCheckBox { get; set; }

		[Outlet]
		AppKit.NSButton _typeMatchMethodCheckBox { get; set; }

		[Outlet]
		AppKit.NSButton _uncombineTitleButton { get; set; }

		[Action ("AcceptDialog:")]
		partial void AcceptDialog (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (_closeButton != null) {
				_closeButton.Dispose ();
				_closeButton = null;
			}

			if (_combineTitlesButton != null) {
				_combineTitlesButton.Dispose ();
				_combineTitlesButton = null;
			}

			if (_downloadFilmInfoButton != null) {
				_downloadFilmInfoButton.Dispose ();
				_downloadFilmInfoButton = null;
			}

			if (_filmRatingTableView != null) {
				_filmRatingTableView.Dispose ();
				_filmRatingTableView = null;
			}

			if (_goToScreeningButton != null) {
				_goToScreeningButton.Dispose ();
				_goToScreeningButton = null;
			}

			if (_typeMatchMethodCheckBox != null) {
				_typeMatchMethodCheckBox.Dispose ();
				_typeMatchMethodCheckBox = null;
			}

			if (_onlyFilmsWithScreeningsCheckBox != null) {
				_onlyFilmsWithScreeningsCheckBox.Dispose ();
				_onlyFilmsWithScreeningsCheckBox = null;
			}

			if (_uncombineTitleButton != null) {
				_uncombineTitleButton.Dispose ();
				_uncombineTitleButton = null;
			}
		}
	}
}
