using System;
using System.Collections.Generic;
using System.IO;
using Foundation;

namespace PresentScreenings.TableView
{
	/// <summary>
    /// List streamer, read/write files based on list of derived objects.
    /// </summary>

    public abstract class ListStreamer : NSObject
    {
        #region Virtual Methods
        public virtual bool ListFileIsMandatory()
        {
            return true;
        }

        public virtual bool ListFileHasHeader()
        {
            return true;
        }

        public virtual string WriteHeader()
        {
            return string.Empty;
        }

        public virtual string Serialize()
        {
            return string.Empty;
        }
        #endregion

        #region Public Methods
        public List<T> ReadListFromFile<T>(string fileName, Func<string, T> lineConstructor) where T : ListStreamer
        {
            var resultList = new List<T> { };
			using (var streamReader = GetStreamReader(fileName))
			{
                if (streamReader != null)
                {
                    string line;
                    bool headerToBeSkipped = ListFileHasHeader();
                    while ((line = streamReader.ReadLine()) != null)
                    {
                        if (headerToBeSkipped)
                        {
                            headerToBeSkipped = false;
                            continue;
                        }
                        try
                        {
                            resultList.Add(lineConstructor(line));
                        }
                        catch (Exception ex)
                        {
                            throw new ApplicationException($"Error when adding an element to {typeof(T)} list based on: {line}", ex);
                        }
                    }
                }
            }
			return resultList;
		}

        public void WriteListToFile<T>(string fileName, List<T> list) where T : ListStreamer
        {
            using (var streamWriter = GetStreamWriter(fileName))
            {
                if (ListFileHasHeader())
                {
                    streamWriter.WriteLine(WriteHeader());
                }
                foreach (var item in list)
                {
                    string line = item.Serialize();
                    streamWriter.WriteLine(line);
                }
                streamWriter.Flush();
            }
        }
        #endregion

        #region Private Methods
        private StreamReader GetStreamReader(string url)
		{
			FileStream fileStream;
			try
			{
                fileStream = new FileStream(url, FileMode.Open, FileAccess.Read);
			}
            catch (FileNotFoundException)
            {
                if (ListFileIsMandatory())
                {
                    throw new FileNotFoundException();
                }
                return null;
            }
            catch (Exception ex)
			{
				throw new Exception(string.Format("Read error, couldn't access file {0}", url), ex);
            }
			return new StreamReader(fileStream);
		}

        private StreamWriter GetStreamWriter(string url)
        {
            FileStream fileStream;
            try
            {
                fileStream = new FileStream(url, FileMode.Create, FileAccess.Write);
            }
            catch (Exception ex)
            {
                throw new Exception(string.Format("Write error, couldn't write file {0}", url), ex);
            }

            return new StreamWriter(fileStream);
        }
        #endregion
    }
}
