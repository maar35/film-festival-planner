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
		AppKit.NSButton _combineTitlesButton { get; set; }

		[Outlet]
		AppKit.NSButton _doneButton { get; set; }

		[Outlet]
		AppKit.NSButton _downloadFilmInfoButton { get; set; }

		[Outlet]
		AppKit.NSTableView _filmRatingTableView { get; set; }

		[Outlet]
		AppKit.NSButton _goToScreeningButton { get; set; }

		[Outlet]
		AppKit.NSButton _typeMatchMethodCheckBox { get; set; }

		[Outlet]
		AppKit.NSButton _uncombineTitleButton { get; set; }

		[Action ("AcceptDialog:")]
		partial void AcceptDialog (Foundation.NSObject sender);
		
		void ReleaseDesignerOutlets ()
		{
			if (_combineTitlesButton != null) {
				_combineTitlesButton.Dispose ();
				_combineTitlesButton = null;
			}

			if (_doneButton != null) {
				_doneButton.Dispose ();
				_doneButton = null;
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

			if (_uncombineTitleButton != null) {
				_uncombineTitleButton.Dispose ();
				_uncombineTitleButton = null;
			}

			if (_downloadFilmInfoButton != null) {
				_downloadFilmInfoButton.Dispose ();
				_downloadFilmInfoButton = null;
			}
		}
	}
}
