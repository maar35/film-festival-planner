﻿// This file has been autogenerated from a class added in the UI designer.

using System;
using Foundation;
using AppKit;
using CoreGraphics;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using static System.Environment;
using System.Net;
using System.Threading.Tasks;

namespace PresentScreenings.TableView
{
    public partial class DownloadFilmInfoController : NSViewController
    {
        #region Constants
        private const float _xMargin = ControlsFactory.HorizontalMargin;
        private const float _xBetweenControls = ControlsFactory.HorizontalPixelsBetweenControls;
        private const float _buttonWidth = ControlsFactory.StandardButtonWidth;
        private const float _yMargin = ControlsFactory.BigVerticalMargin;
        private const float _yBetweenViews = ControlsFactory.VerticalPixelsBetweenViews;
        private const float _yBetweenLabels = ControlsFactory.VerticalPixelsBetweenLabels;
        private const float _labelHeight = ControlsFactory.StandardLabelHeight;
        private const float _buttonHeight = ControlsFactory.StandardButtonHeight;
        private static string _nl = NewLine;
        private const string _dateTimeFormat = "yyyy-MM-dd HH:mm:ss";
        #endregion

        #region Private Variables
        private float _contentWidth;
        private float _yCurr;
        private NSTextField _withoutInfoLabel;
        private NSTextField _progressLabel;
        private NSTextField _activityField;
        private NSScrollView _activityScrollView;
        private NSButton _startButton;
        private NSButton _allFilmsButton;
        private NSButton _closeButton;
        private List<Film> _films;
        private List<Film> _filmsWithoutInfo;
        #endregion

        #region Application Access
        public static AppDelegate App => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public FilmRatingDialogController Presentor;
        #endregion

        #region Constructors
        public DownloadFilmInfoController(IntPtr handle) : base(handle)
        {
            _filmsWithoutInfo = new List<Film>();
        }
        #endregion

        #region Override Methods
        public override void ViewDidLoad()
        {
            base.ViewDidLoad();

            // Get the selected films.
            var indexes = Presentor.FilmRatingTableView.SelectedRows.ToList();
            _films = new List<Film>(indexes.Select(Presentor.GetFilmByIndex));
            _filmsWithoutInfo = GetFilmsWithoutInfo(_films);

            // Set generally usable dimensions.
            var frame = View.Frame;
            _contentWidth = (float)frame.Width - 2 * _xMargin;
            _yCurr = (float)frame.Height;

            // Create the info labels.
            _yCurr -= _yMargin;
            CreateInfoLabels(ref _yCurr);

            //Create the activity scroll view.
            _yCurr -= _yBetweenViews;
            CreateActivityScrollView(ref _yCurr, _yCurr - _yMargin - _buttonHeight - _yBetweenViews);

            // Create the buttons at the bottom of the view.
            _yCurr = _yMargin + _buttonHeight;
            CreateActionButtons(ref _yCurr);
        }

        public override void ViewWillAppear()
        {
            base.ViewWillAppear();

            // Tell the app delegate that we're alive.
            App.DownloadFilmInfoController = this;
        }

        public override void ViewWillDisappear()
        {
            base.ViewWillDisappear();

            // Tell the app delegate that we're gone.
            App.DownloadFilmInfoController = null;
        }
        #endregion

        #region Public Methods

        public static string LogTimeString()
        {
            return $"{DateTime.Now.ToString(_dateTimeFormat)}";
        }
        #endregion

        #region Private Methods
        private List<Film> GetFilmsWithoutInfo(List<Film> films)
        {
            var filmsWithoutInfo = (
                from Film film in _films
                where film.InfoStatus != Film.FilmInfoStatus.Complete
                select ViewController.GetFilmById(film.FilmId)
            ).ToList();
            return filmsWithoutInfo;
        }

        private void CreateInfoLabels(ref float yCurr)
        {
            // Create the selected films count label.
            yCurr -= _labelHeight;
            var selectedCountRect = new CGRect(_xMargin, yCurr, _contentWidth, _labelHeight);
            var selectedCountLabel = ControlsFactory.NewStandardLabel(selectedCountRect);
            selectedCountLabel.StringValue = $"Selected films: {_films.Count}";
            View.AddSubview(selectedCountLabel);

            // Create the films without info count label.
            yCurr -= _yBetweenLabels + _labelHeight;
            var withoutInfoRect = new CGRect(_xMargin, yCurr, _contentWidth, _labelHeight);
            _withoutInfoLabel = ControlsFactory.NewStandardLabel(withoutInfoRect);
            _withoutInfoLabel.StringValue = $"Without info: {_filmsWithoutInfo.Count}";
            View.AddSubview(_withoutInfoLabel);

            //Create the progress label.
            yCurr -= _yBetweenLabels + _labelHeight;
            var progressRect = new CGRect(_xMargin, yCurr, _contentWidth, _labelHeight);
            _progressLabel = ControlsFactory.NewStandardLabel(progressRect);
            SetProgressLabelStringValue();
            View.AddSubview(_progressLabel);
        }

        private void SetProgressLabelStringValue()
        {
            var states = new List<string> { };
            foreach (Film.FilmInfoStatus filmInfoStatus in Enum.GetValues(typeof(Film.FilmInfoStatus)))
            {
                var statusCount = _films.Count(f => f.InfoStatus == filmInfoStatus);
                var statusName = Enum.GetName(typeof(Film.FilmInfoStatus), filmInfoStatus);
                states.Add($"{statusCount} {statusName}");
            }
            _progressLabel.StringValue = string.Join(", ", states);
        }

        private void UpdateWithoutInfoLableStringValue()
        {
            var oldCount = _filmsWithoutInfo.Count;
            _filmsWithoutInfo = GetFilmsWithoutInfo(_films);
            var completedCount = oldCount - _filmsWithoutInfo.Count;
            _withoutInfoLabel.StringValue = $"Processed: {oldCount}, completed: {completedCount}";
        }

        private void CreateActivityScrollView(ref float yCurr, float height)
        {
            _yCurr -= height;
            var docRect = new CGRect(0, 0, _contentWidth, height);
            _activityField = ControlsFactory.NewStandardLabel(docRect);
            _activityField.StringValue = ToDoFilmsString();
            _activityField.CanDrawConcurrently = true;
            var fit = _activityField.SizeThatFits(_activityField.Frame.Size);
            _activityField.SetFrameSize(fit);

            var rect = new CGRect(_xMargin, yCurr, _contentWidth, height);
            _activityScrollView = ControlsFactory.NewStandardScrollView(rect, _activityField);
            View.AddSubview(_activityScrollView);
        }

        private string ToDoFilmsString()
        {
            var builder = new StringBuilder("To do:" + NewLine + NewLine);
            foreach (Film film in _filmsWithoutInfo)
            {
                builder.AppendLine($"{film.ToString()}, {film.InfoStatus.ToString()}");
            }
            return builder.ToString();
        }

        private void CreateActionButtons(ref float yCurr)
        {
            var xCurr = _xMargin;
            yCurr -= _buttonHeight;
            var visitCount = _filmsWithoutInfo.Count;

            // Create the Start button.
            var startButtonRect = new CGRect(xCurr, yCurr, _buttonWidth + 10, _buttonHeight);
            _startButton = ControlsFactory.NewStandardButton(startButtonRect);
            _startButton.Title = $"Visit {visitCount} sites";
            _startButton.LineBreakMode = NSLineBreakMode.ByWordWrapping;
            _startButton.KeyEquivalent = ControlsFactory.EnterKey;
            _startButton.Enabled = visitCount > 0;
            _startButton.Action = new ObjCRuntime.Selector("DownloadFilmInfo:");
            View.AddSubview(_startButton);
            xCurr += (float)_startButton.Frame.Width + _xBetweenControls;

            // Create the All Films button.
            var allFilmsButtonRect = new CGRect(xCurr, yCurr, _buttonWidth, _buttonHeight);
            _allFilmsButton = ControlsFactory.NewStandardButton(allFilmsButtonRect);
            _allFilmsButton.Title = "All films";
            _allFilmsButton.Enabled = false; // Action not implemented.
            _allFilmsButton.Action = new ObjCRuntime.Selector("VisitAllFilms:");
            View.AddSubview(_allFilmsButton);
            xCurr += (float)_allFilmsButton.Frame.Width + _xBetweenControls;

            // Create the Cancel button.
            var cancelButtonRect = new CGRect(xCurr, yCurr, _buttonWidth, _buttonHeight);
            _closeButton = ControlsFactory.NewCancelButton(cancelButtonRect);
            _closeButton.Title = "Close";
            _closeButton.Action = new ObjCRuntime.Selector("CancelDownloadFilmInfo:");
            View.AddSubview(_closeButton);
        }

        private void VisitUrl(Film film)
        {
            var catagory = film.Catagory;
            var url = film.Url;
            var request = WebRequest.Create(url) as HttpWebRequest;
            try
            {
                var filminfo = WebUtility.TryParseUrlSummary(request, url, catagory, film.FilmId);
                if (filminfo != null)
                {
                    filminfo.InfoStatus = Film.FilmInfoStatus.Complete;
                }
            }
            catch (UnparseblePageException)
            {
                FilmInfo.AddNewFilmInfo(film.FilmId, Film.FilmInfoStatus.ParseError);
            }
            catch (WebException)
            {
                FilmInfo.AddNewFilmInfo(film.FilmId, Film.FilmInfoStatus.UrlError);
            }
        }

        private void DownloadFilmInfo()
        {
            // Disable the buttons on the modal dialog, forcing to await feedback.
            _startButton.Enabled = false;
            _closeButton.Enabled = false;

            // Start processing in background.
            var startTime = DateTime.Now;
            var builder = new StringBuilder($"{LogTimeString()} Start analyzing {_filmsWithoutInfo.Count} websites" + _nl);
            Task.Factory.StartNew
            (
                // Download and process on a background thread, allowing the UI
                // to remain responsive.
                () => AsyncDownloadFilmInfo(builder)

            ).ContinueWith
            (
                // Start a new task (this launches a new thread). When the
                // background work is done, continue with this code block.
                task =>
                {
                    var endTime = DateTime.Now;
                    var duration = endTime - startTime;
                    SetProgressLabelStringValue();
                    UpdateWithoutInfoLableStringValue();
                    builder.AppendLine($"{LogTimeString()} Done analyzing, duration {duration.ToString("hh\\:mm\\:ss")}.");
                    _activityField.StringValue = builder.ToString();
                    var fit = _activityField.SizeThatFits(_activityField.Frame.Size);
                    _activityField.SetFrameSize(fit);
                    Presentor.FilmRatingTableView.ReloadData();
                    Presentor.SelectFilms(_films);
                    var yScroll = _activityField.Frame.Height - _activityScrollView.Frame.Height;
                    _activityScrollView.ContentView.ScrollToPoint(new CGPoint(0, yScroll));
                    _closeButton.Enabled = true;
                },
                // Force the code in the ContinueWith block to be run on the
                // calling thread.
                TaskScheduler.FromCurrentSynchronizationContext()
            );
        }

        private void AsyncDownloadFilmInfo(StringBuilder builder)
        {
            foreach (var film in _filmsWithoutInfo)
            {
                VisitUrl(film);
                builder.AppendLine($"{LogTimeString()} - {film.ToString()} - {film.InfoStatus.ToString()}");
            }
        }

        private void CloseView()
        {
            Presentor.DismissViewController(this);
        }
        #endregion

        #region Custom Actions
        [Action("DownloadFilmInfo:")]
        private void DownloadFilmInfo(NSObject sender)
        {
            DownloadFilmInfo();
        }

        [Action("CancelDownloadFilmInfo:")]
        private void CancelDownloadFilmInfo(NSObject sender)
        {
            CloseView();
        }
        #endregion
    }
}
