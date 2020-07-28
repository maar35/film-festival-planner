using System;
using System.Collections.Generic;
using AppKit;
using CoreGraphics;
using Foundation;

namespace PresentScreenings.TableView
{
    public class FilmOutlineLevel : NSObject, IFilmOutlinable
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
            Film,
            FilmScreening,
            OverlappingScreening
        }
        #endregion

        #region Private Variables
        private readonly IFilmOutlinable _filmOutlinable;
        private readonly Level _level;
        #endregion

        #region Properties
        public List<IFilmOutlinable> FilmOutlinables { get; } = new List<IFilmOutlinable> { };
        public Level OutlineLevel => _level;
        public IFilmOutlinable FilmOutlinable => _filmOutlinable;
        static public Action<Screening> GoToScreening { get; private set; }
        #endregion

        #region Constructors
        public FilmOutlineLevel(IFilmOutlinable filmOutlinable, Level level, Action<Screening> goToScreening)
        {
            _filmOutlinable = filmOutlinable;
            _level = level;
            GoToScreening = goToScreening;
        }
        #endregion

        #region Interface Implementations
        public bool ContainsFilmOutlinables()
        {
            return _level == Level.OverlappingScreening ? false : _filmOutlinable.ContainsFilmOutlinables();
        }

        public void SetTitle(NSTextField view)
        {
            if (_level == Level.OverlappingScreening)
            {
                view.StringValue = ((Screening)_filmOutlinable).ScreeningTitle;
            }
        }

        public void SetRating(NSTextField view)
        {
            if (_level == Level.OverlappingScreening)
            {
                view.StringValue = ((Screening)_filmOutlinable).Film.MaxRating.ToString();
            }
        }

        public void SetGo(NSView view)
        {
            if (_level == Level.OverlappingScreening)
            {
                ScreeningsView.DisposeSubViews(view);
                var screening = (Screening)_filmOutlinable;
                var infoButton = new FilmScreeningControl(view.Frame, screening);
                infoButton.ReDraw();
                infoButton.ScreeningInfoAsked += (sender, e) => FilmOutlineLevel.GoToScreening(screening);
                infoButton.Selected = false;
                view.AddSubview(infoButton);
            }
        }

        public void SetInfo(NSTextField view)
        {
            if (_level == Level.OverlappingScreening)
            {
                var screening = (Screening)_filmOutlinable;
                ColorView.SetScreeningColor(screening, view);
                view.StringValue = screening.ScreeningStringForLabel();
                view.StringValue += "  " + FilmInfo.InfoString(((Screening)_filmOutlinable).Film);
                view.LineBreakMode = NSLineBreakMode.TruncatingTail;
            }
        }
        #endregion
    }
}
