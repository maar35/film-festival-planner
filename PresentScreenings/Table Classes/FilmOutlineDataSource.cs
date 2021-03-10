using System;
using System.Collections.Generic;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    public class FilmOutlineDataSource : NSOutlineViewDataSource
    {
        #region Public Variables
        public List<IFilmOutlinable> FilmOutlinables = new List<IFilmOutlinable>();
        #endregion

        #region Constructors
        public FilmOutlineDataSource()
        {
        }
        #endregion

        #region Override Methods
        public override nint GetChildrenCount(NSOutlineView outlineView, NSObject item)
        {
            if (item == null)
            {
                return FilmOutlinables.Count;
            }
            else
            {
                return ((IFilmOutlinable)item).FilmOutlinables.Count;
            }
        }

        public override NSObject GetChild(NSOutlineView outlineView, nint childIndex, NSObject item)
        {
            if (item == null)
            {
                return (NSObject)FilmOutlinables[(int)childIndex];
            }
            else
            {
                return (NSObject)((IFilmOutlinable)item).FilmOutlinables[(int)childIndex];
            }

        }

        public override bool ItemExpandable(NSOutlineView outlineView, NSObject item)
        {
            if (item == null)
            {
                return FilmOutlinables[0].ContainsFilmOutlinables();
            }
            else
            {
                return ((IFilmOutlinable)item).ContainsFilmOutlinables();
            }

        }
        #endregion
    }
}