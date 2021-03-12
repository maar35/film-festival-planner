using System;
using System.Collections.Generic;
using System.Linq;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    public class ScreeningOutlinable : NSObject, IFilmOutlinable
    {
        /// <summary>
        /// Film outline level, contains an IFilmOutlinable and an outline level
        /// indicator.
        /// The IFilmOutlinable is reinstantiated as to behave as designed for
        /// the given outline level.
        /// </summary>

        #region Public Members
        public enum Level
        {
            FilmScreening,
            OverlappingScreening
        }
        #endregion

        #region Properties
        public List<IFilmOutlinable> FilmOutlinables { get; } = new List<IFilmOutlinable> { };
        public Level OutlineLevel { get; }
        public IFilmOutlinable FilmOutlinable { get; }
        public static Action<Screening> GoToScreening { get; private set; }
        public Screening Screening { get; private set; }
        #endregion

        #region Constructors
        public ScreeningOutlinable(Screening screening, Level level)
        {
            Screening = screening;
            OutlineLevel = level;
            GoToScreening = Screening.GoToScreening;
        }
        #endregion

        #region Interface Implementations
        public bool ContainsFilmOutlinables()
        {
            return OutlineLevel == Level.OverlappingScreening ? false
                : OutlineLevel == Level.FilmScreening ? FilmOutlinables.Count > 0
                : false;
        }

        public void SetTitle(NSTextField view)
        {
            switch (OutlineLevel)
            {
                case Level.OverlappingScreening:
                    view.StringValue = Screening.ScreeningTitle;
                    break;
                case Level.FilmScreening:
                    view.StringValue = Screening.ToMenuItemString();
                    view.LineBreakMode = NSLineBreakMode.TruncatingMiddle;
                    break;
            }
        }

        public void SetRating(NSTextField view)
        {
            switch (OutlineLevel)
            {
                case Level.OverlappingScreening:
                    view.StringValue = Screening.Film.MaxRating.ToString();
                    break;
                case Level.FilmScreening:
                    view.StringValue = string.Empty;
                    break;
            }
        }

        public void SetGo(NSView view)
        {
            FilmScreeningControl infoButton;
            ScreeningsView.DisposeSubViews(view);
            infoButton = new FilmScreeningControl(view.Frame, Screening);
            infoButton.ReDraw();
            infoButton.ScreeningInfoAsked += (sender, e) => GoToScreening(Screening);
            infoButton.Selected = ScreeningIsSelected(Screening);
            view.AddSubview(infoButton);
        }

        public void SetInfo(NSTextField view)
        {
            ColorView.SetScreeningColor(Screening, view);
            switch (OutlineLevel)
            {
                case Level.OverlappingScreening:
                    view.StringValue = Screening.ScreeningStringForLabel();
                    view.StringValue += "  " + FilmInfo.InfoString(Screening.Film);
                    break;
                case Level.FilmScreening:
                    view.StringValue = Screening.ScreeningStringForLabel(true);
                    break;
            }
            view.LineBreakMode = NSLineBreakMode.TruncatingTail;
        }

        void IFilmOutlinable.Cleanup()
        {
            AnalyserDialogController.CleanupOutlinables(FilmOutlinables);
        }
        #endregion

        #region Public Methods
        public static bool ScreeningIsSelected(Screening screening)
        {
            AppDelegate app = (AppDelegate)NSApplication.SharedApplication.Delegate;
            return app.Controller.CurrentScreening == screening;
        }

        public void SetOverlappingScreenings()
        {
            if (FilmOutlinables.Count == 0)
            {
                Func<Screening, bool> Attending = s => s.Status == ScreeningInfo.ScreeningStatus.Attending;
                var screenings = ViewController.OverlappingScreenings(Screening, true)
                                               .Where(s => Attending(s))
                                               .OrderByDescending(s => s.Film.MaxRating);
                var level = Level.OverlappingScreening;
                foreach (var screening in screenings)
                {
                    FilmOutlinables.Add(new ScreeningOutlinable(screening, level));
                }
            }
        }
        #endregion
    }
}
