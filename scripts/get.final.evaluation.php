<?php
ini_set("memory_limit", "2048M");

$wordcount2 = 0;
$tweetwordseval = array();
$fileh = fopen("../evaluation/testruns/tweets-test-reference.txt", "r");
while ($line = fgets($fileh)) {
  if (is_numeric($line{0})) {
    $data = explode("\t", str_replace("\n", "", $line));
    $currentid = $data[0];
    $tweetwordseval[$currentid] = array();
  }
  else {
    $data = explode(" ", trim($line));
    $word = $data[0];
    if ($data[2] != "-") {
      if (!strstr($data[2], "_|_")) {
        $alternative = $data[2];
      }
      else {
        $alternative = explode("_|_", $data[2]);
      }
    }
    else {
      $alternative = $word;
    }

    $tweetwordseval[$currentid][$word] = $alternative;
    $wordcount2++;
  }
}
fclose($fileh);

$results = array();

$dir = dir("../evaluation/testruns/participants");
while (($file = $dir->read()) !== false) {
  if (strstr($file, ".txt")) {
    $participant = str_replace(".txt", "", $file);
    $ok = 0;

    $fileh = fopen("participants/" . $file, "r");
    while ($line = fgets($fileh)) {
      if (is_numeric($line{0})) {
        $data = trim($line);
        $currentid = $data;
      }
      else {
        $line = trim($line);
        $data = preg_split("/[\s\t]+/", $line);
        $word = $data[0];
        if ($data[count($data) - 1] != "-") {
          $alternative = $data[count($data) - 1];
        }
        else {
          $alternative = $word;
        }

        if (isset($tweetwordseval[$currentid][$word])) {
          if (($alternative == $tweetwordseval[$currentid][$word]) || (is_array($tweetwordseval[$currentid][$word]) && in_array($alternative, $tweetwordseval[$currentid][$word]))) {
            $ok++;
          }
        }
      }
    }

    $results[$participant] = $ok / $wordcount2;
    fclose($fileh);
  }
}

arsort($results);
$rank = 0;
echo "\n";
foreach ($results as $participant => $precision) {
  echo str_pad(++$rank, 3, " ", STR_PAD_LEFT) . ". " . str_pad($participant . ":", 30) . number_format($precision, 4) . "\n";
}
echo "\n";
?>
