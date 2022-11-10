{-|
Module      : Main
Description : Convert a truth table to NchooseK
Copyright   : (c) 2021 Triad National Security, LLC
License     : BSD-3
Maintainer  : pakin@lanl.gov
Stability   : experimental
Portability : POSIX

__tt2nck__ accepts a truth table expressed as rows of space-separated
@0@s and @1@s (or @F@s and @T@s), provided as a filename named on the
command line or read from standard input.  Comments go from @#@ to the
end of the line.  It outputs this in NchooseK format, best described
by example.  Given a truth table for an AND,

> 0 0 0
> 0 1 0
> 1 0 0
> 1 1 1

the program will output,

> Repetitions: [1,1,2] (4 total)
> Tallies:     [0,1,4]
> Example:     nck([A,B,C,C], [0,1,4])

The first line indicates how many times each variable needs to be
repeated and shows the total number of variable instances needed.  The
second line states the set of the number of variables that must be
/true/.  The third line reformats the first two lines as an NchooseK
constraint, assigning the names @A@, @B@, @C@, etc. to the
truth-table's columns.
-}
module Main
  ( main
  , allSequences
  , allSums
  , uniqueTallies
  , talliesAreDisjoint
  , findValidCoeffs
  , parseTruthTable
  , readTruthTable
  , asConstraint
  ) where

import Control.Parallel.Strategies
import Data.List
import qualified Data.IntSet as IntSet
import qualified Data.Set as Set
import GHC.Conc
import System.Environment
import System.Exit
import System.IO

-- | Return a list of all length-/n/ sequences whose elements are derived
-- (with repetition) from a given set.
--
-- >>> allSequences 3 [0,1]
-- [[0,0,0],[1,0,0],[0,1,0],[1,1,0],[0,0,1],[1,0,1],[0,1,1],[1,1,1]]
allSequences :: Int -> [a] -> [[a]]
allSequences 0 _ = [[]]
allSequences n xs = [h:t | t <- rest, h <- xs]
  where rest = allSequences (n - 1) xs

-- Return all ways of using n natural numbers to represent a sum of x.
allSums' :: Int -> Int -> [[Int]]
allSums' 1 s = [[s]]
allSums' n s = [h:t | h <- [0 .. s], t <- allSums' (n - 1) (s - h)]

-- | Return all ways of using /n/ natural numbers to represent all sums
-- from 1 onward.
--
-- >>> take 100 $ allSums 3
-- [[0,0,1],[0,1,0],[1,0,0],[0,0,2],[0,1,1],[0,2,0],[1,0,1],[1,1,0],[2,0,0],[0,0,3],[0,1,2],[0,2,1],[0,3,0],[1,0,2],[1,1,1],[1,2,0],[2,0,1],[2,1,0],[3,0,0],[0,0,4],[0,1,3],[0,2,2],[0,3,1],[0,4,0],[1,0,3],[1,1,2],[1,2,1],[1,3,0],[2,0,2],[2,1,1],[2,2,0],[3,0,1],[3,1,0],[4,0,0],[0,0,5],[0,1,4],[0,2,3],[0,3,2],[0,4,1],[0,5,0],[1,0,4],[1,1,3],[1,2,2],[1,3,1],[1,4,0],[2,0,3],[2,1,2],[2,2,1],[2,3,0],[3,0,2],[3,1,1],[3,2,0],[4,0,1],[4,1,0],[5,0,0],[0,0,6],[0,1,5],[0,2,4],[0,3,3],[0,4,2],[0,5,1],[0,6,0],[1,0,5],[1,1,4],[1,2,3],[1,3,2],[1,4,1],[1,5,0],[2,0,4],[2,1,3],[2,2,2],[2,3,1],[2,4,0],[3,0,3],[3,1,2],[3,2,1],[3,3,0],[4,0,2],[4,1,1],[4,2,0],[5,0,1],[5,1,0],[6,0,0],[0,0,7],[0,1,6],[0,2,5],[0,3,4],[0,4,3],[0,5,2],[0,6,1],[0,7,0],[1,0,6],[1,1,5],[1,2,4],[1,3,3],[1,4,2],[1,5,1],[1,6,0],[2,0,5],[2,1,4]]
allSums :: Int -> [[Int]]
allSums n
  | n <= 0 = error "Non-positive tally of numbers"
  | otherwise = concatMap (allSums' n) [1..]

-- | Take the inner product of a coefficient list with each
-- truth-table row and return a set of unique inner products.
--
-- >>> uniqueTallies [1,1,2] [[0,0,0],[0,1,1],[1,0,1],[1,1,1]]
-- fromList [0,3,4]
uniqueTallies
  :: [Int]          -- ^ Per-column coefficients
  -> [[Int]]        -- ^ Truth table
  -> IntSet.IntSet  -- ^ Set of unique per-row values
uniqueTallies coeffs rows =
  IntSet.fromList $ map (sum . zipWith (*) coeffs) rows

-- | Return 'True' if no valid and no invalid row share the same inner
-- product with a coefficient list.
--
-- >>> let valids = [[0,0,0],[0,1,0],[1,0,0],[1,1,1]]
-- >>> let invalids = [[0,0,1],[0,1,1],[1,0,1],[1,1,0]]
-- >>> talliesAreDisjoint valids invalids [1,1,1]
-- False
-- >>> talliesAreDisjoint valids invalids [1,1,2]
-- True
talliesAreDisjoint
  :: [[Int]]  -- ^ Valid truth-table rows
  -> [[Int]]  -- ^ Invalid truth-table rows
  -> [Int]    -- ^ Per-column coefficients
  -> Bool     -- ^ Sets of inner products are disjoint
talliesAreDisjoint valids invalids coeffs =
  let
    validTallies = uniqueTallies coeffs valids
    invalidTallies = uniqueTallies coeffs invalids
  in
    IntSet.disjoint validTallies invalidTallies

-- | Split a list into chunks of length n.  (The last chunk may be shorter.)
--
-- >>> chunksOf 3 [1..20]
-- [[1,2,3],[4,5,6],[7,8,9],[10,11,12],[13,14,15],[16,17,18],[19,20]]
chunksOf :: Int -> [a] -> [[a]]
chunksOf n xs
  | n <= 0 = []
  | null xs = []
  | otherwise =
    let
      (first, rest) = splitAt n xs
    in
      (first:chunksOf n rest)

-- | Find lists of NchooseK coefficients, sorted by increasing sum,
-- that correctly partition the truth table into valid and invalid
-- rows.
--
-- >>> take 10 $ findValidCoeffs 5 (odd . sum)
-- [[1,1,1,1,1],[1,1,1,1,3],[1,1,1,3,1],[1,1,3,1,1],[1,3,1,1,1],[3,1,1,1,1],[1,1,1,1,5],[1,1,1,3,3],[1,1,1,5,1],[1,1,3,1,3]]
findValidCoeffs
  :: Int               -- ^ Number of columns in the truth table
  -> ([Int] -> Bool)   -- ^ Return 'True' if a row belongs to the truth table
  -> [[Int]]           -- ^ Infinite list of per-column repetition counts
findValidCoeffs ncols isValid =
  let
    fullTT = allSequences ncols [0, 1]
    allCoeffs = allSums ncols
    allCoeffsChunks = chunksOf 1000 allCoeffs  -- TODO: Don't hard-wire chunk size
    (valids, invalids) = partition isValid fullTT
    coeffsAreValid = talliesAreDisjoint valids invalids
    concurrency = numCapabilities*10   -- Oversubscribe each core to reduce idle time
  in
    filter coeffsAreValid (concat (allCoeffsChunks `using` parBuffer concurrency rdeepseq))

-- Parse a truth-table row into a list of 0s and 1s.
parseTruthTableRow :: String -> Either String [Int]
parseTruthTableRow rowStr =
  let
    noComments = takeWhile (/= '#') rowStr
    parseToken :: String -> Either String Int
    parseToken t =
      case t of
        "0" -> Right 0
        "F" -> Right 0
        "f" -> Right 0
        "1" -> Right 1
        "T" -> Right 1
        "t" -> Right 1
        _ -> Left $ "Failed to parse \"" ++ t ++ "\" as a Boolean value"
  in
    do sequence $ map parseToken $ words noComments

-- | Parse an entire truth table into a list of lists of 0s and 1s,
-- with error-checking.
--
-- >>> parseTruthTable ["F T", "T F"]
-- Right [[0,1],[1,0]]
-- >>> parseTruthTable ["0 0 0", "0 1 1", "1 0 1  # This is my favorite row.", "1 1 0"]
-- Right [[0,0,0],[0,1,1],[1,0,1],[1,1,0]]
-- >>> parseTruthTable ["0 0 0", "0 1", "1 0 1", "1 1 0"]
-- Left "Not all truth-table rows contain the same number of columns"
-- >>> parseTruthTable ["0 0 0", "0 X 1"]
-- Left "Failed to parse \"X\" as a Boolean value"
parseTruthTable :: [String] -> Either String [[Int]]
parseTruthTable rowStrs =
  do
    allRows <- sequence $ map parseTruthTableRow rowStrs  -- Includes empties
    let ttRows = filter (/= []) allRows
    rows <- if ttRows == [] then Left "Truth table is empty" else Right ttRows
    let ncols = (length . head) rows
    sequence $ map (eachLengthIs ncols) rows
      where
        eachLengthIs :: Int -> [Int] -> Either String [Int]
        eachLengthIs n s =
          if length s == n then
            Right s
          else
            Left "Not all truth-table rows contain the same number of columns"

-- | Read and parse a truth table from an open file handle.
readTruthTable :: Handle -> IO [[Int]]
readTruthTable handle =
  do
    progName <- getProgName
    ttStr <- hGetContents handle
    let rowStrs = lines ttStr
    let ttInfo = parseTruthTable rowStrs
    case ttInfo of
      Left msg -> die $ progName ++ ": " ++ msg
      Right tt -> return tt

-- | Format a repetition count and a set of unique tallies as an
-- NchooseK constraint.
--
-- >>> asConstraint [1,2,3] (IntSet.fromList [0,1,5])
-- "nck([A,B,B,C,C,C], [0,1,5])"
asConstraint :: [Int] -> IntSet.IntSet -> String
asConstraint coeffs reps = "nck([" ++ vars ++ "], " ++ ks ++ ")"
  where
    colNames = [reverse (h:t) | t <- [[]] ++ colNames, h <- ['A' .. 'Z']]
    vars = intercalate "," $ concat $ zipWith replicate coeffs colNames
    ks = (show . sort . IntSet.toList) reps

main :: IO ()
main = do
  -- Read a truth table from either standard input or a named file.
  args <- getArgs
  tt <- if length args == 0 then
          readTruthTable stdin
        else
          withFile (args!!0) ReadMode readTruthTable

  -- Perform a brute-force search for NchooseK coefficients.
  let ncols = length (tt!!0)
  let ttSet = Set.fromList tt
  let isValid = flip Set.member ttSet
  let coeffs = head $ findValidCoeffs ncols isValid
  let reps = uniqueTallies coeffs tt
  putStrLn $ "Repetitions: " ++ show coeffs ++ " (" ++ (show . sum) coeffs ++ " total)"
  putStrLn $ "Tallies:     " ++ (show . sort . IntSet.toList) reps
  putStrLn $ "Example:     " ++ asConstraint coeffs reps
