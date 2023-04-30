#use
	
	use File::stat qw(stat);
	
sub LoadFileAsString {
	local ( $file ) = @_;
	local ( $keyfile ) ;
	open( FILE, $file );
	while(<FILE>) {
		s/^ *\n//;
		tr/\t/ /;
		$keyfile = "$keyfile$_";
		}
	
	close ( FILE );
	$keyfile; }
# main
	$cmd_line = $ENV{'QUERY_STRING'} ;
	
	($cmd_line) = @ARGV;
	
	
	$file = $cmd_line ;
	print( STDOUT  ";;;parse file =  $cmd_line  ...  \n" );
	$lasttime = 0;
	$I = 2;
	Parse();
	while( $I < 1 ) {
		$I = $I+1;
		$nowtime = stat($file)->mtime;
		
		
		if ( $nowtime != $lasttime )
		{
			Parse();
			$lasttime = stat($file)->mtime;
			print( STDOUT  "\nlistening and autoparse for file =  $cmd_line  ...  \n" );
		}else{
			}
		
		select(undef, undef, undef, 0.25);
		}
	
	print "done\n";
	
sub PrintTabs{ local ( $num ) = @_;
	local( $i ) = 0;
	while(  $i  < $num ) {
		print( "\t|" );
		$i=$i+1;}
	
	}
sub PrintStack{  local( @stack ) = @_ ;
	
	
	print "";
	PrintTabs(10);
	print "-------- STACK:-------\n";
	foreach $val (@stack){
		$val =~ s/\t*//g;
		$val =~ s/^ +//g;
		PrintTabs(10);
		print( "$val\n" );
		}
	
	PrintTabs(10);
	print "^----------------^\n";
	}
sub Flow{ local ( $lastCode ) = @_;
	$Flow = (     $lastCode =~m/$INPUT/     ||   $lastCode =~m/$LOOP/     ||   $lastCode =~m/$BRANCH/    ||  $lastCode =~ m/$EVENT/ )  ;
	return 1; }
sub getComment { local ( $comment ) = @_;
	$comment  =~ s/\n// ;
	if ( $comment =~ m/^.*#{1}/  )
	{
		$comment =~ s/^.*#{1}//;
	}else{
		$comment ="" ;
		}
	return $comment; }
sub getIndents { local ( $Line ) = @_;
	local( $count )  = 0 ;
	while( $Line =~ m/    / ) {
		$count = $count + 1 ;
		$Line =~ s/    /T/ ;
		
		}
	
	if ( $Line =~ m/T*else:/  ||    $Line =~ m/T*elif.*:/ ||    $Line =~ m/T*except.*:/  ||    $Line =~ m/T*finally.*:/  ||  $Line =~ m/^T*\):/  )
	{
		$count = $count + 1;
		
		}
	return $count; }
sub getCode { local ( $code ) = @_;
	$code  =~ s/\n// ;
	$code =~ s/    //g ;
	$code =~ s/#.*$//;
	return $code ; }
sub peek { local( @stack ) = @_ ;
	local( $ret ) = pop( @stack );
	push( @stack , $ret  );
	if ( $ret eq ""  )
	{
		$ret = -1;
	}else{
		}
	return $ret ;
}
@typestack;
@levelstack;
sub getType{ local( $CODE , $LEVEL    ) = @_;
	my $BRANCH = "^(if|try|with).*[:\(]";
	my $PATH = "^(else|elif|catch|except|final).*:";
	my $LOOP = "^(for|while|do).*:";
	my $INPUT = "^(def.+[:\(])";
	my $CLASS = "^(class)( |\t)";
	my $EVENT = "^(from|import)";
	my $OUTPUT = "^(print).*:";
	
	$level = peek( @levelstack );
	if ( $level == $LEVEL   )
	{
		
		pop( @levelstack ) ;
		print( pop( @typestack ) ) ;
	}else{
		
		}
	
	local( $TYPE ) = "...";
	if ( $CODE =~m/$INPUT/ )
	{
		if ( $LEVEL < 1 )
		{
			$TYPE = "end();\/\/\ninput( $CODE  );\nbranch();\npath();\npath();\/\/ > --------------------------input $LEVEL \n" ;
		}else{
			$TYPE = "end();\/\/\nevent( $CODE  );\/\/\nbranch();\/\/\npath();\/\/\npath();\/\/ " ;
			}
		push( @typestack, "bend();\nend( );\/\/$CODE > ----------------------- $LEVEL\n" );
		push( @levelstack, $LEVEL );
	} elsif ( $CODE =~ m/$CLASS/ ) {
		$TYPE = "end();\/\/;\ninput( $CODE  );\/\/\nbranch();\/\/\npath();\/\/\npath();\/\/ " ;
		push( @typestack, "bend();\/\/\nend( );\/\/$CODE\n" );
		push( @levelstack, $LEVEL );
	} elsif ( $CODE =~ m/$BRANCH/ )  {
		$TYPE = "branch( $CODE );\/\/" ;
		push( @typestack, "bend( );\/\/$CODE\n" );
		push( @levelstack, $LEVEL );
	} elsif ( $CODE =~ m/$LOOP/ )  {
		$TYPE = "loop( $CODE );\/\/" ;
		push( @typestack, "lend( );\/\/$CODE\n" );
		push( @levelstack, $LEVEL );
	} elsif ( $CODE =~ m/$EVENT/ )  {
		$TYPE = "event( $CODE );\/\/" ;
	} elsif ( $CODE =~ m/$OUTPUT/ )  {
		$TYPE = "output( $CODE );\/\/" ;
	} elsif ( $CODE =~ m/$PATH/ )  {
		$TYPE = "path( $CODE );\/\/" ;
	} else {
		$TYPE = "set( $CODE );\/\/" ;
		}
	return $TYPE;  }
sub Parse{
	
	open( FILE, $cmd_line );
	print( ";;;...parseing $cmd_line\n" );
	$lastCount = 0;
	$ParsedFile  = "";
	$multiLine = 0;
	$LINE = 0;
	$PREV_LEVEL = 0;
	$PREV_LINE = 0;
	$LEVEL = 0;
	while(<FILE>) {
		
		$fixLEVEL  = 0 ;
		$LINE = $LINE + 1 ;
		if (  $multiLine ==0 &&   (  $_ =~s/^ *\"\"\"//   || $_ =~s/^ *\'\'\'//   )   )
		{
			if  ( $_ =~s/\"\"\"$/***/   || $_ =~s/\'\'\'$/***/ )
			{
				$_  =~ s/\n// ;
				$COMM =  "$_$PREV_LEVEL" ;
				$_ = ""  ;
				$PREV = $PREV_LEVEL ;
				while( $PREV >=0 ) {
					$PREV = $PREV - 1;
					$_ = "$_\t"  ;
					$LEVEL = $LEVEL+1;
					
					}
				
				$fixLEVEL  = 1 ;
			}else{
				$multiLine = 1 ;
				$_ = "BEGIN MULTI LINE COMMENT\n";
				}
		} else {
			$COMM = getComment( $_ ) ;
			}
		if ( $_ =~ m/^\n$/  ||  $multiLine )
		{
			if ( $multiLine )
			{
				
				if (    ( $_ =~m/\"\"\"/   || $_ =~m/\'\'\'/)   )
				{
					$multiLine = 0 ;
					$_ = "END MULTI LINE COMMENT\n";
					}
				print( "set( );\/\/$_" );
			} else {
				
				}
		}else{
			
			
			if ( $fixLEVEL   )
			{
			}else{
				$LEVEL = getIndents( $_ ) ;
				}
			$CODE = getCode( $_ ) ;
			$MISSED_LEVELS = $PREV_LEVEL - $LEVEL;
			if ( $MISSED_LEVELS  > 1 )
			{
				
				$MISSED = 1;
				while( $MISSED_LEVELS >0 ) {
					$PROC_LEVEL = $PREV_LEVEL-$MISSED ;
					
					
					$TYPE = getType( "BLANK" , $PROC_LEVEL  ) ;
					
					$MISSED = $MISSED + 1 ;
					$MISSED_LEVELS = $MISSED_LEVELS  -1; }
				
				
			}else{
				
				}
			$TYPE = getType( $CODE , $LEVEL  ) ;
			print "$TYPE $COMM\n";
			}
		$PREV_LEVEL = $LEVEL;
		$PREV_LINE = $LINE;
		$PREV_CODE = $CODE;
		}
	
	
	$stack = pop( @typestack );
	while( $stack ) {
		print "$stack";
		$stack = pop( @typestack );
		}
	
	close ( FILE );
	close ( OUTFILE );
	print( "\n$LINE processed lines\n" );
	}
sub printFooter{
	$rootfile = $file;
	$rootfile =~ s/^.*\\//;
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED SESSION INFORMATION\n" );
	print( OUTFILE  "; 255 16777215 65280 16777088 16711680 255 8388608 0 255 255 65535 65280 4210688 \n");
	print( OUTFILE  "$rootfile.py   #\"\"\"  #\"\"\"  \n");
	print( OUTFILE  "; notepad++.exe \n");
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED ALTSESSION INFORMATION\n");
	print( OUTFILE  "; 262 123 765 1694 0 170   379   4294966903    python.key  0");
	}
#  Export  Date: 04:39:35 PM - 30:Apr:2023.

